import os
import time
import logging
import asyncio
import shutil
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Optional
from common.utils.base_workflow import BaseWorkflow
from common.utils.base_service import WorkflowContext
from common.models.job import Job
from ..config.workflow_paths import Workflow1Paths

logger = logging.getLogger(__name__)

class ScriptEventHandler(FileSystemEventHandler):
    def __init__(self, workflow: BaseWorkflow, channel_name: str):
        self.workflow = workflow
        self.channel_name = channel_name
        self.loop = asyncio.new_event_loop()
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        file_path = event.src_path
        if not file_path.lower().endswith('.txt'):
            return
            
        try:
            logger.info(f"Processing new script in channel {self.channel_name}: {file_path}")
            
            # Đợi một chút để đảm bảo file đã được ghi xong
            time.sleep(1)
            
            # Tạo job để tracking
            job = Job(
                file_path=file_path,
                channel_name=self.channel_name
            )
            
            # Tạo context từ job
            context = WorkflowContext(
                workflow_name="workflow1",
                file_path=job.file_path,
                channel_name=job.channel_name
            )
            
            # Di chuyển vào working directory
            channel_paths = self.workflow.paths.get_channel_paths(self.channel_name)
            working_file = os.path.join(channel_paths["working_dir"], os.path.basename(file_path))
            shutil.copy2(file_path, working_file)
            context.file_path = working_file
            
            # Process file
            self.loop.run_until_complete(self.workflow.process(context))
            
        except Exception as e:
            logger.error(f"Error processing script {file_path}: {str(e)}")

class Workflow1Watcher:
    def __init__(self, workflow: BaseWorkflow):
        self.workflow = workflow
        self.observers: Dict[str, Observer] = {}
        
        # Tạo template channel
        self._create_template_channel()
        
    def _create_template_channel(self):
        """Create template channel structure"""
        template_name = "_template"
        template_paths = self.workflow.paths.get_channel_paths(template_name)
        
        # Kiểm tra template channel đã tồn tại chưa
        if os.path.exists(template_paths["channel_dir"]):
            return
            
        # Create all directories
        for path in template_paths.values():
            if isinstance(path, (str, os.PathLike)):
                os.makedirs(path, exist_ok=True)
                
        # Create empty preset.json
        preset_path = template_paths["preset_path"]
        if not os.path.exists(preset_path):
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=4)
                
        print(f"Created template channel at: {template_paths['channel_dir']}")
        print("Copy this template and rename it to create new channels")
        
    def watch_channel(self, channel_name: str):
        """Watch a specific channel"""
        try:
            # Lấy đường dẫn scripts
            channel_paths = self.workflow.paths.get_channel_paths(channel_name)
            scripts_dir = channel_paths["scripts_dir"]
            
            # Tạo thư mục scripts nếu chưa có
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Tạo và start observer
            event_handler = ScriptEventHandler(self.workflow, channel_name)
            observer = Observer()
            observer.schedule(event_handler, scripts_dir, recursive=False)
            observer.start()
            
            self.observers[channel_name] = observer
            logger.info(f"Started watching channel: {channel_name}")
            
        except Exception as e:
            logger.error(f"Error watching channel {channel_name}: {str(e)}")
            
    def start(self):
        """Start watching all channels"""
        try:
            # Lấy danh sách channels từ workflow paths
            channels = self.workflow.paths.get_channels()
            
            # Watch từng channel
            for channel in channels:
                self.watch_channel(channel)
                
            logger.info("Started watching all channels")
            
        except Exception as e:
            logger.error(f"Error starting watcher: {str(e)}")
        
    def stop(self):
        """Stop all observers"""
        for observer in self.observers.values():
            observer.stop()
            observer.join()
        self.observers.clear()
        logger.info("Stopped all watchers")
