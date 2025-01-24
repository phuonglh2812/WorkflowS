import os
import json
import httpx
import shutil
import logging
import asyncio
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
            
            script_name = os.path.splitext(os.path.basename(context.file_path))[0]
            prefix = script_name.split('_KB')[0]
            
            # Prepare form data
            form = {
                'input_folder': working_dir,
                'preset_name': '1'  # Sử dụng preset 1
            }
            
            # Call video API with form-urlencoded
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/api/v1/hook/batch/16_9",
                    data=form,  # Sử dụng data thay vì json
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=1800
                )
                response.raise_for_status()
                task_id = response.json()["task_id"]
                
                # Poll for task completion
                while True:
                    status_response = await client.get(
                        f"{self.api_url}/api/v1/hook/status/{task_id}",
                        timeout=30
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    if status_data["status"] == "completed":
                        # Di chuyển tất cả file của prefix sang final
                        self._move_files_to_final(working_dir, final_dir, prefix)
                        
                        # Trả về đường dẫn video trong final dir
                        video_name = os.path.basename(status_data["output_path"])
                        final_video_path = os.path.join(final_dir, video_name)
                        
                        return {
                            "video_path": final_video_path
                        }
                    elif status_data["status"] == "failed":
                        raise Exception(f"Video generation failed: {status_data.get('error', 'Unknown error')}")
                        
                    await asyncio.sleep(5)  # Wait 5 seconds before next poll
                    
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            raise
