import os
import sys
import time
import json
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Optional, Set
import shutil
import asyncio

# Add root path to sys.path
ROOT_PATH = str(Path(__file__).parent.parent.parent.parent)
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from common.utils.base_service import BaseService, WorkflowContext
from common.models.job import Job
from ..config.workflow_paths import Workflow3Paths

logger = logging.getLogger(__name__)

class Workflow3Watcher:
    def __init__(self):
        try:
            self.paths = Workflow3Paths()
            logger.info(f"Workflow3 ROOT_PATH: {self.paths.ROOT_PATH}")
            
            # Import Workflow3 ở đây để tránh circular import
            from ..main import Workflow3
            self.workflow = Workflow3()
            self.observers: Dict[str, Observer] = {}
            self.handlers: Dict[str, ScriptEventHandler] = {}
            
            # Lấy event loop hiện tại 
            self.loop = asyncio.get_event_loop()
                
        except Exception as e:
            logger.error(f"Error initializing Workflow3Watcher: {str(e)}")
            raise
            
    def start_channel(self, channel_name: str):
        """Start watching một channel cụ thể"""
        try:
            # Get paths for channel
            channel_paths = self.paths.get_channel_paths(channel_name)
            scripts_dir = channel_paths["scripts_dir"]
            
            # Create handler and observer for this channel
            handler = ScriptEventHandler(self.workflow, channel_name, self.loop)
            observer = Observer()
            observer.schedule(handler, scripts_dir, recursive=False)
            observer.start()
            
            # Store handler and observer
            self.handlers[channel_name] = handler
            self.observers[channel_name] = observer
            
            logger.info(f"Started watching channel {channel_name} at {scripts_dir}")
            
        except Exception as e:
            logger.error(f"Error starting channel {channel_name}: {str(e)}")
            raise
            
    def start_all_channels(self):
        """Start watching tất cả channels"""
        try:
            # Get list of all channels
            channels = self.paths.get_channels()
            logger.info(f"Found channels: {channels}")
            
            # Start watching each channel
            for channel in channels:
                channel_paths = self.paths.get_channel_paths(channel)
                scripts_dir = channel_paths["scripts_dir"]
                self.start_channel(channel)
                logger.info(f"Started watching channel {channel} at {scripts_dir}")
                
            logger.info("All channel watchers started successfully")
                
        except Exception as e:
            logger.error(f"Error starting all channels: {str(e)}")
            raise
            
    def stop(self):
        """Stop tất cả observers"""
        try:
            for observer in self.observers.values():
                observer.stop()
                observer.join()
                
            if self.loop and self.loop.is_running():
                self.loop.stop()
                
        except Exception as e:
            logger.error(f"Error stopping watchers: {str(e)}")
            raise
            
    def run_event_loop(self):
        """Run event loop của workflow này"""
        try:
            if not self.loop.is_running():
                self.loop.run_forever()
        except Exception as e:
            logger.error(f"Error running event loop: {str(e)}")
            raise


class ScriptEventHandler(FileSystemEventHandler):
    """Handler xử lý các sự kiện file trong thư mục Scripts"""
    
    def __init__(self, workflow: 'Workflow3', channel_name: str, loop: asyncio.AbstractEventLoop):
        self.workflow = workflow
        self.channel_name = channel_name
        self.loop = loop
        self.processing_files: Set[str] = set()
        self.processing_prefixes: Set[str] = set()  # Track prefixes đang xử lý
        self.processing_lock = asyncio.Lock()  # Lock để tránh xử lý đồng thời

    def on_created(self, event):
        """Xử lý khi có file mới được tạo"""
        if event.is_directory:
            return
            
        file_path = event.src_path
        if not self._should_process_file(file_path):
            return
            
        logger.info(f"New file detected: {file_path}")
        self._handle_new_file(file_path)
        
    def _should_process_file(self, file_path: str) -> bool:
        """Kiểm tra xem có nên xử lý file này không"""
        try:
            file_name = os.path.basename(file_path).lower()
            
            # Chỉ xử lý file .txt
            if not file_name.endswith('.txt'):
                return False
                
            # Chỉ xử lý file hook hoặc kb
            patterns = ['_hook.txt', '_Hook.txt', '_kb.txt', '_KB.txt', '_Kb.txt']
            if not any(p.lower() in file_name for p in patterns):
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking file {file_path}: {str(e)}")
            return False
            
    def _find_matching_file(self, directory: str, prefix: str, pattern: str) -> Optional[str]:
        """Tìm file phù hợp với prefix và pattern, không phân biệt hoa thường"""
        try:
            # Lấy tất cả file trong thư mục
            files = os.listdir(directory)
            # Tìm file có prefix và pattern phù hợp
            for file in files:
                if (file.lower().startswith(prefix.lower()) and 
                    any(p.lower() in file.lower() for p in ['_hook.txt', '_Hook.txt', '_kb.txt', '_KB.txt', '_Kb.txt'])):
                    if pattern.lower() in file.lower():
                        return os.path.join(directory, file)
            return None
        except Exception as e:
            logger.error(f"Error finding matching file in {directory}: {str(e)}")
            return None

    def _handle_new_file(self, file_path: str):
        """Xử lý file mới"""
        try:
            # Kiểm tra xem có nên xử lý file này không
            if not self._should_process_file(file_path):
                return
                
            # Thêm vào danh sách đang xử lý
            self.processing_files.add(file_path)
            
            file_name = os.path.basename(file_path).lower()
            prefix = file_name.split('_')[0]
            directory = os.path.dirname(file_path)
            
            # Nếu là file hook, đợi file kb tương ứng
            if any(p in file_name.lower() for p in ['_hook.txt', '_Hook.txt']):
                hook_file = file_path
                kb_file = self._find_matching_file(directory, prefix, '_kb')
                
                if kb_file:
                    logger.info(f"Found KB file for {file_name}, processing pair...")
                    self._process_file_pair_async(prefix, hook_file, kb_file)
                else:
                    logger.info(f"Waiting for KB file for {file_name}...")
                    
            # Nếu là file kb, đợi file hook tương ứng
            elif any(p in file_name.lower() for p in ['_kb.txt', '_KB.txt', '_Kb.txt']):
                kb_file = file_path
                hook_file = self._find_matching_file(directory, prefix, '_hook')
                
                if hook_file:
                    logger.info(f"Found hook file for {file_name}, processing pair...")
                    self._process_file_pair_async(prefix, hook_file, kb_file)
                else:
                    logger.info(f"Waiting for hook file for {file_name}...")
                    
        except Exception as e:
            logger.error(f"Error handling new file {file_path}: {str(e)}")
            
        finally:
            # Xóa khỏi danh sách đang xử lý
            self.processing_files.discard(file_path)

    async def _process_file_pair(self, prefix: str, hook_file: str, kb_file: str):
        """Xử lý cặp file hook và kb"""
        try:
            # Kiểm tra xem prefix đã đang được xử lý chưa
            async with self.processing_lock:
                if prefix in self.processing_prefixes:
                    logger.info(f"Prefix {prefix} is already being processed, skipping...")
                    return
                self.processing_prefixes.add(prefix)
                
            hook_file = str(hook_file)
            kb_file = str(kb_file)
            
            if os.path.exists(hook_file) and os.path.exists(kb_file):
                # Xử lý hook file trước
                hook_context = WorkflowContext(
                    workflow_name="workflow3",
                    file_path=hook_file,
                    channel_name=self.channel_name
                )
                await self.workflow.process_hook(hook_context)
                
                # Sau đó xử lý kb file
                kb_context = WorkflowContext(
                    workflow_name="workflow3",
                    file_path=kb_file,
                    channel_name=self.channel_name
                )
                await self.workflow.process_kb(kb_context)  # Gọi process_kb thay vì process
                
                logger.info(f"Successfully processed file pair with prefix {prefix}")
                
            # Xóa prefix khỏi danh sách đang xử lý
            async with self.processing_lock:
                self.processing_prefixes.remove(prefix)
            
        except Exception as e:
            logger.error(f"Error processing file pair with prefix {prefix}: {str(e)}")
            # Đảm bảo prefix được xóa khỏi danh sách trong mọi trường hợp
            async with self.processing_lock:
                self.processing_prefixes.discard(prefix)
            
    def _process_file_pair_async(self, prefix: str, hook_file: str, kb_file: str):
        """Xử lý cặp file hook và kb bất đồng bộ"""
        try:
            # Tạo coroutine và schedule nó chạy trong event loop
            asyncio.run_coroutine_threadsafe(
                self._process_file_pair(prefix, hook_file, kb_file),
                self.loop
            )
        except Exception as e:
            logger.error(f"Error scheduling file pair processing: {str(e)}")
            # Xóa các file khỏi danh sách đang xử lý
            self.processing_files.discard(hook_file)
            self.processing_files.discard(kb_file)
