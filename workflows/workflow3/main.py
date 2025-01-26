import os
import sys
import asyncio
import logging
import subprocess
from typing import Dict, Optional, List
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from common.utils.base_service import BaseService, WorkflowContext

# Add root path to sys.path
ROOT_PATH = str(Path(__file__).parent.parent.parent)
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from .config.workflow_paths import Workflow3Paths
from .services.voice_service import VoiceService
from .services.video_service import VideoService

logger = logging.getLogger(__name__)

class Workflow3(BaseService):
    def __init__(self):
        super().__init__()
        self.paths = Workflow3Paths()
        self.voice_service = VoiceService(self.paths)
        self.video_service = VideoService(self.paths)
        
    async def process_hook(self, context: WorkflowContext) -> Dict:
        """Process hook file"""
        try:
            # Lấy kết quả từ voice service
            voice_result = await self.voice_service.process_hook(context)
            context.results['VoiceService'] = voice_result
            
            # Tạo thumbnail và overlay
            channel_paths = self.paths.get_channel_paths(context.channel_name)
            script_name = os.path.splitext(os.path.basename(context.file_path))[0]
            prefix = script_name.split('_Hook')[0]
            
            # Lấy font và base image từ thư mục Assets
            assets_dir = channel_paths["assets_dir"]
            font_files = [f for f in os.listdir(assets_dir) if f.endswith('.ttf')]
            image_files = [f for f in os.listdir(assets_dir) if f.endswith('.png')]
            
            if not font_files or not image_files:
                raise FileNotFoundError(f"Missing font or base image in {assets_dir}")
                
            font_path = os.path.join(assets_dir, font_files[0])
            base_image = os.path.join(assets_dir, image_files[0])
            
            # Sử dụng đường dẫn tuyệt đối cho ThumbMakerV.py
            thumbmaker_path = Path("D:/AutomateWorkFlow/WorkflowFile/WorkflowS/ThumbMakerV.py")
            working_dir = channel_paths["working_dir"]
            
            cmd = [
                "python",
                str(thumbmaker_path),
                "--base_image", base_image,
                "--text_file", context.file_path,
                "--output_dir", working_dir,
                "--font_path", font_path
            ]
            
            logger.info(f"Running ThumbMaker with command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"ThumbMaker failed: {result.stderr}")
            
            # Kiểm tra output files
            thumbnail_path = os.path.join(working_dir, f"{script_name}_thumbnail.png")
            overlay_path = os.path.join(working_dir, f"{script_name}.png")
            
            if not os.path.exists(thumbnail_path) or not os.path.exists(overlay_path):
                raise FileNotFoundError(f"ThumbMaker did not generate expected output files")
            
            return {
                "thumbnail_path": thumbnail_path,
                "overlay_path": overlay_path,
                "wav_file": voice_result["wav_file"]
            }
            
        except Exception as e:
            logger.error(f"Error processing hook file: {str(e)}")
            raise
            
    async def process_kb(self, context: WorkflowContext) -> Dict:
        """Process KB file"""
        try:
            # Lấy kết quả từ voice service
            voice_result = await self.voice_service.process(context)
            context.results['VoiceService'] = voice_result
            
            # Lấy kết quả từ video service
            video_result = await self.video_service.process(context)
            context.results['VideoService'] = video_result
            
            return context.results
            
        except Exception as e:
            logger.error(f"Error processing KB file: {str(e)}")
            raise

    async def process(self, context: WorkflowContext) -> Dict:
        """Process a single file based on its type"""
        try:
            file_name = os.path.basename(context.file_path).lower()
            logger.info(f"Processing file: {file_name}")
            
            if '_hook.txt' in file_name:
                logger.info(f"Processing as hook file: {file_name}")
                result = await self.process_hook(context)
                logger.info(f"Successfully processed hook file: {file_name}")
                return result
            elif '_kb.txt' in file_name:
                logger.info(f"Processing as KB file: {file_name}")
                result = await self.process_kb(context)
                logger.info(f"Successfully processed KB file: {file_name}")
                return result
            else:
                raise ValueError(f"Unknown file type: {file_name}")
                
        except Exception as e:
            logger.error(f"Error processing file {context.file_path}: {str(e)}")
            raise

app = FastAPI()
workflow = Workflow3()

@app.on_event("startup")
async def startup_event():
    """Khởi tạo workflow watchers"""
    try:
        # Import workflow_watcher ở đây để tránh circular import
        from .services.workflow_watcher import WorkflowWatcher
        
        # Khởi tạo workflow watchers cho từng channel
        watchers = []
        for channel in workflow.paths.CHANNELS:
            channel_paths = workflow.paths.get_channel_paths(channel)
            watcher = WorkflowWatcher(
                workflow=workflow,
                channel_name=channel,
                input_dir=channel_paths["input_dir"],
                pattern="*_Hook.txt",
                kb_pattern="*_KB.txt"
            )
            watchers.append(watcher)
            
        # Start tất cả watchers
        for watcher in watchers:
            watcher.start()
            
    except Exception as e:
        logger.error(f"Error starting workflow watchers: {str(e)}")
        raise

@app.get("/")
def read_root():
    return {"Hello": "World"}
