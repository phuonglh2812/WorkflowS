import os
import json
import httpx
import shutil
import logging
import asyncio
import time
import subprocess
import re
from typing import Dict, Optional
from common.utils.base_service import BaseService, WorkflowContext
from ..config.workflow_paths import Workflow2Paths

logger = logging.getLogger(__name__)

class VideoService(BaseService):
    def __init__(self, paths: Workflow2Paths):
        super().__init__()
        self.paths = paths
        self.api_url = paths.api_urls["video_api"]
        
    def _move_files_to_final(self, working_dir: str, final_dir: str, prefix: str):
        """Di chuyển tất cả file của prefix từ working sang final"""
        try:
            # Lấy danh sách file trong working dir
            files = os.listdir(working_dir)
            
            # Lọc các file có prefix cần di chuyển
            prefix_files = [f for f in files if f.startswith(prefix)]
            
            # Di chuyển từng file
            for file_name in prefix_files:
                src = os.path.join(working_dir, file_name)
                dst = os.path.join(final_dir, file_name)
                logger.info(f"Moving {src} to {dst}")
                shutil.move(src, dst)
                
        except Exception as e:
            logger.error(f"Error moving files to final: {str(e)}")
            raise
        
    def _move_script_files(self, channel_paths: Dict[str, str], prefix: str, target_dir: str):
        """Di chuyển các file script có prefix vào thư mục target (Completed hoặc Error)"""
        try:
            scripts_dir = channel_paths["scripts_dir"]
            # Lấy danh sách file trong scripts dir
            files = os.listdir(scripts_dir)
            
            # Lọc các file có prefix cần di chuyển
            prefix_files = [f for f in files if f.startswith(prefix)]
            
            # Di chuyển từng file
            for file_name in prefix_files:
                src = os.path.join(scripts_dir, file_name)
                dst = os.path.join(target_dir, file_name)
                logger.info(f"Moving script {src} to {dst}")
                shutil.move(src, dst)
                
        except Exception as e:
            logger.error(f"Error moving script files: {str(e)}")
            raise

    def _handle_error(self, channel_paths: Dict[str, str], prefix: str, error_msg: str):
        """Xử lý khi có lỗi: di chuyển tất cả file đã tạo vào Error"""
        try:
            # Di chuyển file từ working dir sang error dir
            working_dir = channel_paths["working_dir"]
            error_dir = channel_paths["error_dir"]
            
            # Lấy danh sách file trong working dir
            files = os.listdir(working_dir)
            
            # Lọc các file có prefix cần di chuyển
            prefix_files = [f for f in files if f.startswith(prefix)]
            
            # Di chuyển từng file
            for file_name in prefix_files:
                src = os.path.join(working_dir, file_name)
                dst = os.path.join(error_dir, file_name)
                logger.info(f"Moving error file {src} to {dst}")
                shutil.move(src, dst)
            
            # Di chuyển các file script vào Error
            self._move_script_files(channel_paths, prefix, error_dir)
            
            # Ghi log lỗi vào file trong error dir
            error_log = os.path.join(error_dir, f"{prefix}_error.log")
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write(f"Error occurred at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Error message: {error_msg}\n")
                
        except Exception as e:
            logger.error(f"Error handling error state: {str(e)}")
            raise

    def _normalize_text(self, text: str) -> str:
        """
        Chuẩn hóa văn bản:
        - Loại bỏ các ký tự đặc biệt
        - Giữ lại chữ, số, khoảng trắng
        - Giới hạn độ dài
        """
        import re
        
        # Loại bỏ các ký tự đặc biệt, giữ lại chữ, số, khoảng trắng
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        
        # Loại bỏ multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Giới hạn độ dài (ví dụ: 200 ký tự)
        return normalized[:200]

    def _read_hook_content(self, hook_file: str) -> str:
        """Đọc nội dung từ file hook"""
        try:
            with open(hook_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading hook file: {str(e)}")
            raise

    def _update_video_metadata(self, video_file: str, hook_file: str, channel_name: str) -> None:
        """Cập nhật metadata cho file video bằng FFmpeg"""
        temp_file = None
        try:
            # Đọc nội dung hook file
            content = self._read_hook_content(hook_file)
            
            # Lấy title từ dòng đầu tiên của hook content
            title = content.split('\n')[0].strip()
            
            # Chuẩn hóa title và content
            normalized_title = self._normalize_text(title)
            normalized_content = self._normalize_text(content)
            
            # Tạo temporary file path
            temp_file = video_file + ".temp.mp4"

            # Các metadata cần thêm vào video
            metadata_args = [
                "-metadata", f"title={normalized_title}",
                "-metadata", f"artist={channel_name}",
                "-metadata", f"comment={normalized_content}",
                "-metadata", f"description={normalized_content}",
                "-metadata", f"genre={channel_name.lower()}",
                "-metadata", "rating=5.0"
            ]

            # Lệnh FFmpeg để thêm metadata mà không làm thay đổi chất lượng video
            ffmpeg_cmd = [
                "ffmpeg", "-i", video_file,
                "-map", "0", "-c", "copy"
            ] + metadata_args + [temp_file]

            # Thực thi lệnh FFmpeg
            result = subprocess.run(
                ffmpeg_cmd, 
                capture_output=True, 
                text=True,
                check=True
            )

            # Thay thế file gốc bằng file mới có metadata
            os.replace(temp_file, video_file)

            logger.info(f"Updated metadata for video: {video_file}")

        except Exception as e:
            logger.error(f"Error updating video metadata: {str(e)}")
            # Cleanup temp file if exists
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            raise

    async def process(self, context: WorkflowContext) -> Dict:
        """Process video với timeout 30 minutes"""
        try:
            # Lấy kết quả từ voice service
            if not hasattr(context, 'results') or 'VoiceService' not in context.results:
                raise ValueError("Voice result not found in context")
            
            voice_result = context.results['VoiceService']
            
            # Get channel paths và prefix
            channel_paths = self.paths.get_channel_paths(context.channel_name)
            working_dir = channel_paths["working_dir"]
            final_dir = channel_paths["final_dir"]
            completed_dir = channel_paths["completed_dir"]
            
            script_name = os.path.splitext(os.path.basename(context.file_path))[0]
            prefix = script_name.split('_KB')[0]
            
            # Load preset từ file
            preset_file = self.paths.get_preset_path(context.channel_name)
            if not os.path.exists(preset_file):
                raise FileNotFoundError(f"Preset file not found: {preset_file}")
                
            with open(preset_file, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            
            # Chuẩn bị form data
            form = {
                'input_folder': working_dir,
                # Lấy 'preset_name' từ preset
                'preset_name': preset_data['video_settings']['preset_name']
            }

            # Lấy bg_path từ context nếu có, nếu không thì lấy từ preset (nếu có)
            bg_path = getattr(context, 'bg_path', None)
            if not bg_path:
                # fallback từ preset (nếu có)
                bg_path = preset_data['video_settings'].get('bg_path')
            
            # Nếu bg_path tồn tại => đưa vào form
            if bg_path:
                form['bg_path'] = bg_path

            logger.info(f"Sending request to {self.api_url}/api/v1/hook/batch/16_9")
            logger.info(f"Form data: {form}")
            
            # Gọi video API (form-urlencoded)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/hook/batch/16_9",
                    data=form,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=1800  # 30 phút
                )
                response.raise_for_status()
                task_id = response.json()["task_id"]
                logger.info(f"Got task_id: {task_id}")
                
                # Poll for task completion
                while True:
                    status_url = f"{self.api_url}/api/v1/hook/status/{task_id}"
                    logger.info(f"Checking status at: {status_url}")
                    status_response = await client.get(status_url, timeout=1800)
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    logger.info(f"Status response: {status_data}")
                    
                    if status_data["status"] == "completed":
                        logger.info("Video processing completed, moving files to final")
                        # Di chuyển tất cả file của prefix sang final
                        self._move_files_to_final(working_dir, final_dir, prefix)
                        
                        # Di chuyển các file script vào Final
                        self._move_script_files(channel_paths, prefix, final_dir)
                        
                        # Lấy tên video từ output_paths của API
                        if not status_data.get("output_paths"):
                            raise Exception("No output video path in API response")
                        video_name = os.path.basename(status_data["output_paths"][0])
                        final_video_path = os.path.join(self.paths.VIDEO_DIR, "final", video_name)
                        logger.info(f"Final video path: {final_video_path}")
                        
                        # Di chuyển video vào thư mục final của channel
                        channel_video_path = os.path.join(final_dir, video_name)
                        shutil.move(final_video_path, channel_video_path)
                        logger.info(f"Moved final video to channel's final directory: {channel_video_path}")
                        
                        # Thêm metadata cho video
                        hook_file = os.path.join(channel_paths["final_dir"], f"{prefix}_Hook.txt")
                        self._update_video_metadata(channel_video_path, hook_file, context.channel_name)
                        logger.info(f"Added metadata for video: {channel_video_path}")
                        
                        return {"video_path": channel_video_path}
                    
                    elif status_data["status"] == "failed":
                        error_msg = f"Video generation failed: {status_data.get('error', 'Unknown error')}"
                        logger.error(error_msg)
                        # Xử lý lỗi và di chuyển file vào Error
                        self._handle_error(channel_paths, prefix, error_msg)
                        raise Exception(error_msg)
                        
                    logger.info("Video still processing, waiting 15 minutes...")
                    await asyncio.sleep(900)  # Wait 15 minutes before next poll

        except Exception as e:
            error_msg = f"Error processing video: {str(e)}"
            logger.error(error_msg)
            # Xử lý lỗi và di chuyển file vào Error
            self._handle_error(channel_paths, prefix, error_msg)
            raise

