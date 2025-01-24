import os
from typing import Optional

class WorkflowBasePaths:
    def __init__(self, workflow_name: str):
        self.WORKFLOW_NAME = workflow_name
        
        # Base directory (Level 1)
        self.ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.WORKFLOW_DIR = os.path.join(self.ROOT_DIR, workflow_name)
        
        # Create workflow directory
        os.makedirs(self.WORKFLOW_DIR, exist_ok=True)
            
    def get_channel_dir(self, channel_name: str) -> str:
        """Get base directory for a specific channel (Level 2)"""
        return os.path.join(self.WORKFLOW_DIR, channel_name)
        
    def setup_channel(self, channel_name: str):
        """Setup directory structure for a new channel"""
        channel_dir = self.get_channel_dir(channel_name)
        
        # Channel subdirectories (Level 3)
        scripts_dir = os.path.join(channel_dir, "Scripts")
        working_dir = os.path.join(channel_dir, "Working")
        completed_dir = os.path.join(channel_dir, "Completed")
        error_dir = os.path.join(channel_dir, "Error")
        final_dir = os.path.join(channel_dir, "Final")
        assets_dir = os.path.join(channel_dir, "Assets")
        
        # Config files
        voice_config = os.path.join(channel_dir, "config.json")
        preset_config = os.path.join(channel_dir, "preset.json")
        
        # Assets subdirectories
        overlay1_dir = os.path.join(assets_dir, "Overlay1")  # Overlay cố định
        overlay2_dir = os.path.join(assets_dir, "Overlay2")  # Overlay random
        
        # Create all channel directories
        directories = [
            scripts_dir, 
            working_dir, 
            completed_dir, 
            error_dir, 
            final_dir, 
            assets_dir,
            overlay1_dir,
            overlay2_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
        return {
            "channel_dir": channel_dir,
            "scripts_dir": scripts_dir,
            "working_dir": working_dir,
            "completed_dir": completed_dir,
            "error_dir": error_dir,
            "final_dir": final_dir,
            "assets_dir": assets_dir,
            "overlay1_dir": overlay1_dir,  # Thêm đường dẫn overlay1
            "overlay2_dir": overlay2_dir,   # Thêm đường dẫn overlay2
            "voice_config": voice_config,
            "preset_config": preset_config
        }
        
    def get_channel_paths(self, channel_name: str) -> dict:
        """Get all paths for a specific channel"""
        channel_dir = self.get_channel_dir(channel_name)
        assets_dir = os.path.join(channel_dir, "Assets")
        
        return {
            "channel_dir": channel_dir,
            "scripts_dir": os.path.join(channel_dir, "Scripts"),
            "working_dir": os.path.join(channel_dir, "Working"),
            "completed_dir": os.path.join(channel_dir, "Completed"),
            "error_dir": os.path.join(channel_dir, "Error"),
            "final_dir": os.path.join(channel_dir, "Final"),
            "assets_dir": assets_dir,
            "overlay1_dir": os.path.join(assets_dir, "Overlay1"),  # Thêm đường dẫn overlay1
            "overlay2_dir": os.path.join(assets_dir, "Overlay2"),   # Thêm đường dẫn overlay2
            "voice_config": os.path.join(channel_dir, "config.json"),
            "preset_config": os.path.join(channel_dir, "preset.json")
        }
