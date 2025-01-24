import os
import json
import random
import httpx
import time
import asyncio
import uuid
from typing import Dict, Tuple, Optional
from common.utils.base_service import BaseService, WorkflowContext
from ..config.workflow_paths import Workflow1Paths
import shutil

class VideoService(BaseService):
    def __init__(self, paths: Workflow1Paths):
        super().__init__()
        self.paths = paths
        self.api_url = paths.api_urls["video_api"]
        
    def _get_overlay1(self, channel_name: str) -> str:
        """Lấy file png duy nhất từ thư mục overlay1"""
        channel_paths = self.paths.get_channel_paths(channel_name)
        overlay1_dir = channel_paths["overlay1_dir"]
        overlay1_path = os.path.join(overlay1_dir, 'overlay1.png')
        
        if not os.path.exists(overlay1_path):
            raise ValueError(f"Không tìm thấy overlay1.png trong {overlay1_dir}")
            
        return overlay1_path
        
    def _get_random_overlay2(self, channel_name: str) -> Tuple[str, str]:
        """Lấy ngẫu nhiên một file overlay2
        Returns:
            Tuple[str, str]: (full_path, file_name)
        """
        channel_paths = self.paths.get_channel_paths(channel_name)
        overlay2_dir = channel_paths["overlay2_dir"]
        
        if not os.path.exists(overlay2_dir):
            raise ValueError(f"Không tìm thấy thư mục overlay2 cho channel {channel_name}")
            
        overlay_files = [f for f in os.listdir(overlay2_dir) if f.endswith('.png')]
        if not overlay_files:
            raise ValueError(f"Không tìm thấy file overlay2 nào trong {overlay2_dir}")
            
        selected_file = random.choice(overlay_files)
        return os.path.join(overlay2_dir, selected_file), selected_file

    def _move_overlay_to_final(self, channel_name: str, overlay_name: str, video_name: str):
        """Di chuyển overlay đã sử dụng vào thư mục final và đổi tên"""
        channel_paths = self.paths.get_channel_paths(channel_name)
        source_path = os.path.join(channel_paths["overlay2_dir"], overlay_name)
        final_dir = channel_paths["final_dir"]
        os.makedirs(final_dir, exist_ok=True)
        
        # Tạo tên mới cho overlay: tên_video_overlay.png
        new_name = f"{os.path.splitext(video_name)[0]}_overlay.png"
        target_path = os.path.join(final_dir, new_name)
        
        shutil.copy2(source_path, target_path)  # copy2 giữ nguyên metadata
        self.logger.info(f"Đã copy overlay từ {overlay_name} đến {target_path}")

    def _get_preset_name(self, channel_name: str) -> str:
        """Lấy preset name từ config"""
        try:
            preset_path = self.paths.get_preset_path(channel_name)
            if os.path.exists(preset_path):
                with open(preset_path, 'r', encoding='utf-8') as f:
                    preset_data = json.load(f)
                    return preset_data.get('video_settings', {}).get('preset_name', 'default')
            return 'default'
        except Exception as e:
            self.logger.error(f"Error loading preset: {str(e)}")
            return 'default'

    async def _check_task_status(self, task_id: str, client: httpx.AsyncClient) -> Tuple[bool, Optional[str], Optional[str]]:
        """Kiểm tra trạng thái của task
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: (is_completed, error_message, output_path)
        """
        try:
            response = await client.get(
                f"{self.api_url}/api/v1/api/process/status/{task_id}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Log trạng thái
            self.logger.debug(f"Task {task_id} status: {data}")
            
            if data.get("status") == "completed":
                return True, None, data.get("output_path")
            elif data.get("status") == "failed":
                return True, data.get("error", "Unknown error"), None
            else:
                return False, None, None
                
        except Exception as e:
            self.logger.warning(f"Error checking task status: {str(e)}")
            return False, str(e), None

    def _move_working_files_to_final(self, channel_name: str, prefix: str):
        """Di chuyển tất cả file trong working có prefix tương ứng vào final"""
        channel_paths = self.paths.get_channel_paths(channel_name)
        working_dir = channel_paths["working_dir"]
        final_dir = channel_paths["final_dir"]
        
        # Đảm bảo thư mục final tồn tại
        os.makedirs(final_dir, exist_ok=True)
        
        # Lấy danh sách file trong working có prefix tương ứng
        working_files = [f for f in os.listdir(working_dir) 
                        if f.startswith(prefix) and os.path.isfile(os.path.join(working_dir, f))]
        
        for file_name in working_files:
            source_path = os.path.join(working_dir, file_name)
            target_path = os.path.join(final_dir, file_name)
            
            try:
                # Copy file vào final
                shutil.copy2(source_path, target_path)
                self.logger.info(f"Đã copy file {file_name} vào final")
                
                # Xóa file gốc
                try:
                    os.remove(source_path)
                    self.logger.debug(f"Đã xóa file gốc: {source_path}")
                except Exception as e:
                    self.logger.warning(f"Không thể xóa file gốc {source_path}: {str(e)}")
                    
            except Exception as e:
                self.logger.error(f"Không thể copy file {file_name} vào final: {str(e)}")

    async def process(self, context: WorkflowContext) -> Dict:
        """Process video với timeout 30 minutes"""
        try:
            # Lấy kết quả từ voice service
            if not hasattr(context, 'results') or 'VoiceService' not in context.results:
                raise ValueError("Voice result not found in context")
            
            voice_result = context.results['VoiceService']
            wav_file = voice_result['wav_file']
            srt_file = voice_result['srt_file']
            
            self.logger.info(f"Processing video for audio: {wav_file}")
            
            # Get channel paths
            channel_paths = self.paths.get_channel_paths(context.channel_name)
            script_name = os.path.splitext(os.path.basename(context.file_path))[0]
            prefix = script_name.split('_KB')[0]
            
            # Tạo unique ID cho video
            unique_id = str(uuid.uuid4())[:8]
            output_name = f"{prefix}_{unique_id}.mp4"
            
            # Đường dẫn final trong kênh
            channel_final_path = os.path.join(channel_paths["final_dir"], output_name)
            self.logger.debug(f"Video sẽ được lưu vào: {channel_final_path}")
            
            # Get overlay files
            overlay1 = self._get_overlay1(context.channel_name)
            overlay2_path, overlay2_name = self._get_random_overlay2(context.channel_name)
            self.logger.debug(f"Using overlays: {overlay1} and {overlay2_path}")
            
            # Get preset name
            preset_name = self._get_preset_name(context.channel_name)
            self.logger.debug(f"Using preset: {preset_name}")
            
            # Call video API
            payload = {
                "request": "",  # API không cần request type
                "audio_path": wav_file,
                "subtitle_path": srt_file,
                "overlay1_path": overlay1,
                "overlay2_path": overlay2_path,
                "preset_name": preset_name,
                "output_name": output_name  # API sẽ lưu vào thư mục của nó
            }
            
            async with httpx.AsyncClient() as client:
                # Start task
                self.logger.debug(f"Starting video task with payload: {payload}")
                response = await client.post(
                    f"{self.api_url}/api/v1/api/process/make",
                    headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                    data=payload,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                task_id = data.get("task_id")
                
                if not task_id:
                    raise ValueError("No task_id in API response")
                    
                self.logger.info(f"Video task started with ID: {task_id}")
                
                # Poll task status
                max_attempts = 180  # 30 minutes (10s interval)
                attempt = 0
                api_output_path = None
                
                while attempt < max_attempts:
                    is_completed, error, output_path = await self._check_task_status(task_id, client)
                    
                    if error:
                        raise ValueError(f"Video task failed: {error}")
                        
                    if is_completed and output_path:
                        self.logger.info(f"Video task {task_id} completed, output at: {output_path}")
                        api_output_path = output_path
                        break
                        
                    attempt += 1
                    await asyncio.sleep(10)  # Chờ 10s trước khi kiểm tra lại
                    
                if attempt >= max_attempts:
                    raise ValueError(f"Video task {task_id} timed out after 30 minutes")
                    
                if not api_output_path:
                    raise ValueError("Video task completed but no output path returned")
            
            # Copy overlay2 đã sử dụng vào thư mục final của kênh
            move_attempts = 2
            for attempt in range(move_attempts):
                try:
                    self._move_overlay_to_final(context.channel_name, overlay2_name, output_name)
                    self.logger.info(f"Overlay2 đã được copy thành công")
                    break
                except Exception as e:
                    self.logger.warning(f"Lần thử copy overlay2 {attempt + 1}/{move_attempts} thất bại: {str(e)}")
                    if attempt == move_attempts - 1:
                        self.logger.error("Không thể copy overlay2 sau 2 lần thử")
                    await asyncio.sleep(3)
            
            # Copy video từ thư mục API về thư mục final của kênh
            move_attempts = 2
            for attempt in range(move_attempts):
                try:
                    if not os.path.exists(api_output_path):
                        raise ValueError(f"Video file not found at {api_output_path}")
                        
                    os.makedirs(os.path.dirname(channel_final_path), exist_ok=True)
                    shutil.copy2(api_output_path, channel_final_path)
                    self.logger.info(f"Video đã được copy vào kênh thành công: {channel_final_path}")
                    
                    # Xóa file gốc sau khi copy thành công
                    try:
                        os.remove(api_output_path)
                        self.logger.debug(f"Đã xóa file từ API: {api_output_path}")
                    except Exception as e:
                        self.logger.warning(f"Không thể xóa file từ API {api_output_path}: {str(e)}")
                    
                    break
                except Exception as e:
                    self.logger.warning(f"Lần thử copy video {attempt + 1}/{move_attempts} thất bại: {str(e)}")
                    if attempt == move_attempts - 1:
                        self.logger.error("Không thể copy video sau 2 lần thử")
                    await asyncio.sleep(3)
            
            # Di chuyển các file working vào final
            self._move_working_files_to_final(context.channel_name, prefix)
            
            return {
                'video_file': channel_final_path,
                'overlay_file': overlay2_path
            }
            
        except Exception as e:
            self.logger.error(f"Video processing failed: {str(e)}")
            raise ValueError(f"Video processing failed: {str(e)}")
