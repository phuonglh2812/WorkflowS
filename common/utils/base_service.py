from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import shutil
import logging

class WorkflowContext:
    """Context object passed between workflow steps"""
    def __init__(self, workflow_name: str, file_path: str, channel_name: str):
        self.workflow_name = workflow_name
        self.file_path = file_path
        self.channel_name = channel_name
        self._state: Dict[str, Any] = {}
        
        # Setup logging
        self.logger = logging.getLogger(f"workflow.{workflow_name}")
        
    def update_state(self, key: str, value: Any):
        """Update workflow state"""
        self._state[key] = value
        
    def get_state(self, key: str) -> Optional[Any]:
        """Get value from workflow state"""
        return self._state.get(key)
        
    def move_to_working(self, source_path: str, filename: str = None) -> str:
        """Move file to working directory"""
        if filename is None:
            filename = os.path.basename(source_path)
            
        paths = self.get_state('channel_paths')
        if not paths:
            raise ValueError("Channel paths not found in context")
            
        target_path = os.path.join(paths["working_dir"], filename)
        self._move_file(source_path, target_path)
        return target_path
        
    def move_to_completed(self, source_path: str, filename: str = None) -> str:
        """Move file to completed directory"""
        if filename is None:
            filename = os.path.basename(source_path)
            
        paths = self.get_state('channel_paths')
        if not paths:
            raise ValueError("Channel paths not found in context")
            
        target_path = os.path.join(paths["completed_dir"], filename)
        self._move_file(source_path, target_path)
        return target_path
        
    def move_to_error(self, source_path: str, filename: str = None) -> str:
        """Move file to error directory"""
        if filename is None:
            filename = os.path.basename(source_path)
            
        paths = self.get_state('channel_paths')
        if not paths:
            raise ValueError("Channel paths not found in context")
            
        target_path = os.path.join(paths["error_dir"], filename)
        self._move_file(source_path, target_path)
        return target_path
        
    def move_to_final(self, source_path: str, filename: str = None) -> str:
        """Move file to final directory"""
        if filename is None:
            filename = os.path.basename(source_path)
            
        paths = self.get_state('channel_paths')
        if not paths:
            raise ValueError("Channel paths not found in context")
            
        target_path = os.path.join(paths["final_dir"], filename)
        self._move_file(source_path, target_path)
        return target_path
        
    def _move_file(self, source: str, target: str):
        """Move file with logging"""
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(source, target)
            self.logger.info(f"Moved file from {source} to {target}")
        except Exception as e:
            self.logger.error(f"Failed to move file from {source} to {target}: {str(e)}")
            raise

class BaseService(ABC):
    """Base class for all workflow services"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def process(self, context: WorkflowContext) -> Dict:
        """Process the workflow step"""
        pass
        
    async def cleanup(self, context: WorkflowContext):
        """Cleanup after processing (optional)"""
        pass
