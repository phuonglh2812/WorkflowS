import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Optional, Set

# Add root path to sys.path
ROOT_PATH = str(Path(__file__).parent.parent.parent.parent)
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from common.utils.base_service import BaseService, WorkflowContext
from common.models.job import Job
from ..config.workflow_paths import Workflow2Paths

logger = logging.getLogger(__name__)

class Workflow2Watcher:
    def __init__(self):
        try:
            paths = Workflow2Paths()
            logger.info(f"Workflow2 ROOT_PATH: {paths.ROOT_PATH}")
            
            # Import Workflow2 ở đây để tránh circular import
            from .. import main
            self.workflow = main.Workflow2()
            self.observers: Dict[str, Observer] = {}
            self.handlers: Dict[str, ScriptEventHandler] = {}
            
            # Lấy event loop hiện tại hoặc tạo mới
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
        except Exception as e:
            logger.error(f"Error initializing Workflow2Watcher: {str(e)}")
            raise
            
    def start_channel(self, channel_name: str):
        """Start watching một channel"""
        try:
            # Lấy script dir của channel
            channel_paths = self.workflow.paths.get_channel_paths(channel_name)
            script_dir = channel_paths["scripts_dir"]
            
            # Create observer for this channel
            event_handler = ScriptEventHandler(self.workflow, channel_name)
            event_handler.loop = self.loop  # Set event loop cho handler
            
            observer = Observer()
            observer.schedule(event_handler, script_dir, recursive=False)
            
            self.observers[channel_name] = observer
            self.handlers[channel_name] = event_handler
            
            logger.info(f"Started watching channel {channel_name} at {script_dir}")
            
        except Exception as e:
            logger.error(f"Error starting channel {channel_name}: {str(e)}")
            raise
            
    def start_all_channels(self):
        """Start watching tất cả channels"""
        try:
            # Start watching từng channel
            for channel in self.workflow.paths.CHANNELS:
                self.start_channel(channel)
                
            # Start tất cả observers
            for observer in self.observers.values():
                observer.start()
                
            logger.info("All channel watchers started")
            
        except Exception as e:
            logger.error(f"Error starting all channels: {str(e)}")
            raise
            
    def run_event_loop(self):
        """Run event loop"""
        try:
            logger.info("Starting event loop")
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Error running event loop: {str(e)}")
            raise
            
    def stop(self):
        """Stop tất cả watchers"""
        try:
            # Stop tất cả observers
            for observer in self.observers.values():
                observer.stop()
                
            # Wait for all observers to complete
            for observer in self.observers.values():
                observer.join()
                
            logger.info("All watchers stopped")
            
        except Exception as e:
            logger.error(f"Error stopping watchers: {str(e)}")
            raise

class ScriptEventHandler(FileSystemEventHandler):
    def __init__(self, workflow, channel_name: str):
        self.workflow = workflow
        self.channel_name = channel_name
        self.processing_prefixes: Set[str] = set()  # Track prefixes đang xử lý
        self.processing_lock = asyncio.Lock()  # Lock để tránh xử lý đồng thời
        self.loop = None  # Event loop sẽ được set sau
        
    def _get_file_prefix(self, file_path: str) -> str:
        """Lấy prefix từ tên file"""
        return os.path.splitext(os.path.basename(file_path))[0].split('_')[0]
        
    def _is_pair_complete(self, prefix: str) -> bool:
        """Kiểm tra xem cặp file có đầy đủ không"""
        channel_paths = self.workflow.paths.get_channel_paths(self.channel_name)
        script_dir = channel_paths["scripts_dir"]
        
        # Kiểm tra cả hook và kb file
        hook_exists = os.path.exists(os.path.join(script_dir, f"{prefix}_Hook.txt"))
        kb_exists = os.path.exists(os.path.join(script_dir, f"{prefix}_KB.txt"))
        
        return hook_exists and kb_exists
        
    async def _process_file_pair(self, prefix: str):
        """Xử lý một cặp file hoàn chỉnh"""
        try:
            # Đánh dấu prefix đang xử lý
            async with self.processing_lock:
                if prefix in self.processing_prefixes:
                    logger.info(f"Prefix {prefix} is already being processed")
                    return
                self.processing_prefixes.add(prefix)
            
            # Lấy cặp file
            channel_paths = self.workflow.paths.get_channel_paths(self.channel_name)
            script_dir = channel_paths["scripts_dir"]
            
            hook_file = os.path.join(script_dir, f"{prefix}_Hook.txt")
            kb_file = os.path.join(script_dir, f"{prefix}_KB.txt")
            # Ép sang str (nếu script_dir có thể là Path)
            hook_file = str(hook_file)
            kb_file = str(kb_file)
            hook_context = WorkflowContext(
                workflow_name="workflow2",
                file_path=hook_file,
                channel_name=self.channel_name
            )
            if os.path.exists(hook_file) and os.path.exists(kb_file):
                # Xử lý hook file trước
                hook_context = WorkflowContext(
                    workflow_name="workflow2",
                    file_path=hook_file,
                    channel_name=self.channel_name
                )
                await self.workflow.process_hook(hook_context)
                
                # Sau đó xử lý kb file
                kb_context = WorkflowContext(
                    workflow_name="workflow2",
                    file_path=kb_file,
                    channel_name=self.channel_name
                )
                await self.workflow.process(kb_context)
                
            # Xóa prefix khỏi danh sách đang xử lý
            async with self.processing_lock:
                self.processing_prefixes.remove(prefix)
            
        except Exception as e:
            logger.error(f"Error processing file pair with prefix {prefix}: {str(e)}")
            # Đảm bảo prefix được xóa khỏi danh sách trong mọi trường hợp
            async with self.processing_lock:
                self.processing_prefixes.discard(prefix)
            
    def on_created(self, event):
        """Handle file creation event"""
        if event.is_directory:
            return
            
        try:
            file_path = event.src_path
            logger.info(f"Processing new script in channel {self.channel_name}: {file_path}")
            
            # Đợi một chút để đảm bảo file đã được ghi xong
            time.sleep(1)
            
            # Lấy prefix và kiểm tra cặp file
            prefix = self._get_file_prefix(file_path)
            
            if self._is_pair_complete(prefix):
                logger.info(f"Found complete pair for prefix {prefix}, processing...")
                
                # Sử dụng event loop từ Workflow2Watcher
                if self.loop:
                    asyncio.run_coroutine_threadsafe(
                        self._process_file_pair(prefix),
                        self.loop
                    )
                else:
                    logger.error("Event loop not set in handler")
                
            else:
                logger.info(f"Pair for prefix {prefix} is not complete yet, waiting for pair...")
                
        except Exception as e:
            logger.error(f"Error processing script {file_path}: {str(e)}")
            try:
                # Di chuyển file lỗi vào error dir
                error_file = os.path.join(self.workflow.paths.get_channel_paths(self.channel_name)["error_dir"], os.path.basename(file_path))
                shutil.move(file_path, error_file)
            except Exception as move_error:
                logger.error(f"Error moving file to error dir: {str(move_error)}")
