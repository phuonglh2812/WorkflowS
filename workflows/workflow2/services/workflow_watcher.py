import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Optional, Set
import shutil

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
            
            # Lấy hoặc tạo event loop
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
            
            # Create handler and observer for this channel
            event_handler = ScriptEventHandler(self.workflow, channel_name, self.loop)
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
            
    def stop(self):
        """Stop tất cả watchers"""
        try:
            # Stop tất cả observers
            for observer in self.observers.values():
                observer.stop()
                observer.join()
                
            # Stop event loop nếu đang chạy
            if self.loop and self.loop.is_running():
                self.loop.stop()
                
        except Exception as e:
            logger.error(f"Error stopping watchers: {str(e)}")
            raise

    def run_event_loop(self):
        """Run event loop"""
        try:
            logger.info("Starting event loop")
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Error running event loop: {str(e)}")
            raise
            
class ScriptEventHandler(FileSystemEventHandler):
    def __init__(self, workflow, channel_name: str, loop: asyncio.AbstractEventLoop):
        self.workflow = workflow
        self.channel_name = channel_name
        self.processing_lock = asyncio.Lock()
        self.processing_queue = asyncio.Queue()
        self.processing_task = None
        self.processing_prefixes: Set[str] = set()
        self.loop = loop
        
        # Sử dụng loop để tạo task
        self.processing_task = self.loop.create_task(self._process_queue())
        
    def _get_file_prefix(self, file_path: str) -> str:
        """Lấy prefix từ tên file"""
        return os.path.splitext(os.path.basename(file_path))[0].split('_')[0]
        
    def _is_pair_complete(self, prefix: str) -> bool:
        """Kiểm tra xem cặp file có đầy đủ không"""
        channel_paths = self.workflow.paths.get_channel_paths(self.channel_name)
        script_dir = channel_paths["scripts_dir"]
        
        # Kiểm tra cả hook và kb file
        hook_files = [f for f in os.listdir(script_dir) if f.startswith(f"{prefix}_") and '_Hook.txt' in f]
        kb_files = [f for f in os.listdir(script_dir) if f.startswith(f"{prefix}_") and '_KB.txt' in f]
        
        return bool(hook_files and kb_files)
        
    async def _process_queue(self):
        """Xử lý queue theo thứ tự FIFO"""
        while True:
            try:
                # Lấy file pair từ queue
                prefix, hook_file, kb_file = await self.processing_queue.get()
                
                try:
                    # Kiểm tra xem prefix này đã được xử lý chưa
                    async with self.processing_lock:
                        if prefix in self.processing_prefixes:
                            logger.info(f"Prefix {prefix} is already being processed")
                            continue
                        self.processing_prefixes.add(prefix)
                    
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
                    
                    # Di chuyển file đã xử lý sang thư mục completed
                    channel_paths = self.workflow.paths.get_channel_paths(self.channel_name)
                    completed_dir = channel_paths["completed_dir"]
                    
                    # Di chuyển hook file
                    hook_filename = os.path.basename(hook_file)
                    shutil.move(
                        hook_file, 
                        os.path.join(completed_dir, hook_filename)
                    )
                    
                    # Di chuyển kb file
                    kb_filename = os.path.basename(kb_file)
                    shutil.move(
                        kb_file, 
                        os.path.join(completed_dir, kb_filename)
                    )
                    
                    logger.info(f"Processed file pair: {prefix}")
                
                except Exception as e:
                    logger.error(f"Error processing file pair {prefix}: {str(e)}")
                
                finally:
                    # Luôn đảm bảo prefix được xóa khỏi danh sách
                    async with self.processing_lock:
                        self.processing_prefixes.discard(prefix)
                    
                    # Đánh dấu task trong queue đã hoàn thành
                    self.processing_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in queue processing: {str(e)}")
                await asyncio.sleep(1)  # Tránh busy loop
    
    def on_created(self, event):
        """Xử lý khi có file mới được tạo"""
        if event.is_directory:
            return
            
        file_path = event.src_path
        file_name = os.path.basename(file_path).lower()
        
        # Chỉ xử lý file txt
        if not file_name.endswith('.txt'):
            return
        
        # Lấy prefix
        prefix = self._get_file_prefix(file_path)
        
        # Kiểm tra xem có đủ cặp file không
        channel_paths = self.workflow.paths.get_channel_paths(self.channel_name)
        script_dir = channel_paths["scripts_dir"]
        
        # Tìm hook và kb file
        hook_files = [os.path.join(script_dir, f) for f in os.listdir(script_dir) 
                      if f.startswith(f"{prefix}_") and '_Hook.txt' in f]
        kb_files = [os.path.join(script_dir, f) for f in os.listdir(script_dir) 
                    if f.startswith(f"{prefix}_") and '_KB.txt' in f]
        
        # Nếu có đủ cặp file, thêm vào queue
        if hook_files and kb_files:
            logger.info(f"Found complete pair for prefix {prefix}, adding to queue")
            # Sử dụng run_coroutine_threadsafe để thêm vào queue
            asyncio.run_coroutine_threadsafe(
                self.processing_queue.put((prefix, hook_files[0], kb_files[0])), 
                self.loop
            )
