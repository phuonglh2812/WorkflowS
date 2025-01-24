import os
import json
from typing import Dict, List
from pathlib import Path

class BasePathConfig:
    """Base configuration for paths that all workflows will inherit from"""
    
    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self._load_config()
        self.setup_base_paths()
        
    def _load_config(self):
        """Load config from config.json"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
        
        if not os.path.exists(config_path):
            raise ValueError(f"Config file not found at {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        self.ROOT_PATH = config['root_path']
        self.api_urls = config['api_urls']
        
        # Tạo các thư mục cần thiết
        os.makedirs(self.ROOT_PATH, exist_ok=True)
        
    def setup_base_paths(self):
        """Setup basic directory structure"""
        self.ROOT_DIR = Path(self.ROOT_PATH)
        self.WORKFLOW_DIR = self.ROOT_DIR / "workflows" / self.workflow_name
        self.DATA_DIR = self.ROOT_DIR / "data" / self.workflow_name
        self.CONFIG_DIR = self.WORKFLOW_DIR / "config"
        self.INPUT_DIR = self.DATA_DIR / "input"
        self.OUTPUT_DIR = self.DATA_DIR / "output"
        
        # Thêm các đường dẫn từ workflow hiện tại
        self.SCRIPTS_DIR = self.INPUT_DIR / "scripts"
        self.AUDIO_DIR = self.OUTPUT_DIR / "audio"
        self.VIDEO_DIR = self.OUTPUT_DIR / "video"
        self.SRT_DIR = self.OUTPUT_DIR / "srt"
        self.FINAL_DIR = self.OUTPUT_DIR / "final"
        
    def ensure_directories(self):
        """Create all necessary directories"""
        dirs = [
            self.WORKFLOW_DIR,
            self.DATA_DIR,
            self.CONFIG_DIR,
            self.INPUT_DIR,
            self.OUTPUT_DIR,
            self.SCRIPTS_DIR,
            self.AUDIO_DIR,
            self.VIDEO_DIR,
            self.SRT_DIR,
            self.FINAL_DIR
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    @property
    def CHANNELS_DIR(self) -> str:
        """Thư mục chứa các channel"""
        return os.path.join(self.ROOT_PATH, "channels")
        
    @property 
    def LOGS_DIR(self) -> str:
        """Thư mục chứa logs"""
        return os.path.join(self.ROOT_PATH, "logs")
        
    @property
    def TEMP_DIR(self) -> str:
        """Thư mục tạm thời"""
        return os.path.join(self.ROOT_PATH, "temp")
        
    def get_channel_base_path(self, channel_name: str) -> str:
        """Lấy đường dẫn gốc của channel"""
        return os.path.join(self.CHANNELS_DIR, channel_name)
        
    def get_channel_names(self) -> List[str]:
        """Lấy danh sách tên các channel từ thư mục channels"""
        if not os.path.exists(self.CHANNELS_DIR):
            return []
            
        # Chỉ lấy các thư mục, bỏ qua file
        return [d for d in os.listdir(self.CHANNELS_DIR) 
                if os.path.isdir(os.path.join(self.CHANNELS_DIR, d))]
                
    def validate_channel(self, channel_name: str) -> bool:
        """Kiểm tra xem channel có tồn tại và hợp lệ không"""
        channel_path = self.get_channel_base_path(channel_name)
        
        # Kiểm tra thư mục channel có tồn tại
        if not os.path.exists(channel_path):
            return False
            
        # Kiểm tra có phải là thư mục
        if not os.path.isdir(channel_path):
            return False
            
        # Kiểm tra có config.json và preset.json
        if not os.path.exists(os.path.join(channel_path, "config.json")):
            return False
            
        if not os.path.exists(os.path.join(channel_path, "preset.json")):
            return False
            
        return True
        
    def get_channels(self) -> List[str]:
        """Get list of all channels"""
        if not os.path.exists(self.INPUT_DIR):
            return []
            
        channels = []
        for item in os.listdir(self.INPUT_DIR):
            if os.path.isdir(os.path.join(self.INPUT_DIR, item)) and not item.startswith('_'):
                channels.append(item)
                
        return channels
