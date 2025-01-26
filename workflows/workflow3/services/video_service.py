import os
import json
import httpx
import shutil
import logging
import asyncio
import time
from typing import Dict, Optional
from common.utils.base_service import BaseService, WorkflowContext
from ..config.workflow_paths import Workflow3Paths

logger = logging.getLogger(__name__)

class VideoService(BaseService):
    def __init__(self, paths: Workflow3Paths):
        super().__init__()
        self.paths = paths
        self.api_url = str(paths.api_urls["video_api"])
        
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

    async def process(self, context: WorkflowContext) -> Dict:
        """Process video với timeout 30 minutes"""
        try:
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
            
            # Prepare form data
            form = {
                'input_folder': working_dir,
                'preset_name': preset_data['video_settings']['preset_name'],  # Lấy preset_name từ preset
            }
            
            logger.info(f"Sending request to {self.api_url}/api/v1/hook/batch/9_16")
            logger.info(f"Form data: {form}")
            
            # Call video API with form-urlencoded
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/hook/batch/9_16",
                    data=form,  # Sử dụng data thay vì json
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=1800
                )
                response.raise_for_status()
                task_id = response.json()["task_id"]
                logger.info(f"Got task_id: {task_id}")
                
                # Poll for task completion
                while True:
                    status_url = f"{self.api_url}/api/v1/hook/status/{task_id}"
                    logger.info(f"Checking status at: {status_url}")
                    status_response = await client.get(
                        status_url,
                        timeout=1800
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    logger.info(f"Status response: {status_data}")
                    
                    if status_data["status"] == "completed":
                        logger.info("Video processing completed, moving files to final")
                        # Di chuyển tất cả file của prefix sang final
                        self._move_files_to_final(working_dir, final_dir, prefix)
                        
                        # Di chuyển các file script vào Completed
                        self._move_script_files(channel_paths, prefix, completed_dir)
                        
                        # Tạo đường dẫn video theo format mặc định
                        timestamp = str(int(time.time()))
                        video_name = f"{prefix.lower()}_{timestamp}.mp4"
                        final_video_path = os.path.join(self.paths.VIDEO_DIR, "final", video_name)
                        logger.info(f"Final video path: {final_video_path}")
                        
                        # Di chuyển video vào thư mục final của channel
                        shutil.move(final_video_path, os.path.join(final_dir, video_name))
                        logger.info(f"Moved final video to channel's final directory: {os.path.join(final_dir, video_name)}")
                        
                        return {
                            "video_path": os.path.join(final_dir, video_name)
                        }
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
