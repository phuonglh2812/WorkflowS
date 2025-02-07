import os
import json
from pathlib import Path
from typing import Dict, List
from common.config.base_paths import BasePathConfig

class Workflow3Paths(BasePathConfig):
    def __init__(self):
        # Khởi tạo base class trước
        super().__init__(workflow_name="workflow3")
        
        # Khởi tạo các đường dẫn (dạng Path để chúng ta còn mkdir dễ)
        self.ROOT_DIR = Path(os.getenv("WORKFLOW_ROOT", "D:/AutomateWorkFlow/workflow3"))
        self.PANDORA_DIR = Path(os.getenv("PANDORA_DIR", "D:/AutomateWorkFlow/WorkflowFile/Pandrator"))
        self.VIDEO_DIR = Path(os.getenv("VIDEO_DIR", "D:/AutomateWorkFlow/WorkflowFile/VideoMakerS_Files"))
        self.FINAL_DIR = Path(os.getenv("FINAL_DIR", "D:/AutomateWorkFlow/WorkflowFile/VideoMakerS_Files/final"))

        # Load api_urls from config.json
        config_file = self.ROOT_DIR / "config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
                api_urls = config.get("api_urls", {})
                
                # Whisper configuration
                self.WHISPER_SERVER_HOST = api_urls.get("whisper_server_host", "localhost")
                self.WHISPER_SERVER_PORT = api_urls.get("whisper_server_port", 5004)
                self.WHISPER_SERVER_URL = f"http://{self.WHISPER_SERVER_HOST}:{self.WHISPER_SERVER_PORT}"
                self.WHISPER_API_TIMEOUT = api_urls.get("whisper_api_timeout", 1200)  # 20 minutes in seconds
                
                # TTS configuration
                self.TTS_SERVER_HOST = api_urls.get("tts_server_host", "localhost")
                self.TTS_SERVER_PORT = api_urls.get("tts_server_port", 5006)
                self.TTS_SERVER_URL = f"http://{self.TTS_SERVER_HOST}:{self.TTS_SERVER_PORT}"
                self.TTS_API_TIMEOUT = api_urls.get("tts_api_timeout", 1800)  # 30 minutes in seconds
        else:
            # Default Whisper configuration
            self.WHISPER_SERVER_HOST = "localhost"
            self.WHISPER_SERVER_PORT = 5004
            self.WHISPER_SERVER_URL = f"http://{self.WHISPER_SERVER_HOST}:{self.WHISPER_SERVER_PORT}"
            self.WHISPER_API_TIMEOUT = 1200  # 20 minutes in seconds
            
            # Default TTS configuration
            self.TTS_SERVER_HOST = "localhost"
            self.TTS_SERVER_PORT = 5006
            self.TTS_SERVER_URL = f"http://{self.TTS_SERVER_HOST}:{self.TTS_SERVER_PORT}"
            self.TTS_API_TIMEOUT = 1800  # 30 minutes in seconds

        # Tự động tìm các channel
        self.CHANNELS = self.discover_channels()
        
        # Tạo các channel nếu chưa tồn tại
        for channel in self.CHANNELS:
            self.get_channel_paths(channel)        
            
        # Tạo template channel
        self.setup_template_channel()

    def get_channel_paths(self, channel_name: str) -> Dict[str, str]:
        """Get all paths for a specific channel, 
           cuối cùng trả về dict chứa chuỗi (str) thay vì Path."""
        channel_base = self.ROOT_DIR / channel_name
        
        paths = {
            "channel_dir": channel_base,
            "scripts_dir": channel_base / "Scripts",
            "working_dir": channel_base / "Working",
            "completed_dir": channel_base / "Completed",
            "error_dir": channel_base / "Error",
            "final_dir": channel_base / "Final",
            
            "assets_dir": channel_base / "Assets",
            "config_file": channel_base / "config.json",
            "preset_file": channel_base / "preset.json",
            
            "video_final": self.FINAL_DIR
        }
        
        # Tạo các thư mục nếu chưa tồn tại (chỉ mkdir nếu không phải file .json)
        for p in paths.values():
            if p.suffix != '.json':
                p.mkdir(parents=True, exist_ok=True)
        
        # Cuối cùng chuyển tất cả sang str trước khi trả về
        return {key: str(path_obj) for key, path_obj in paths.items()}

    def get_preset_path(self, channel_name: str) -> str:
        """Get path (string) to preset file"""
        channel_paths = self.get_channel_paths(channel_name)
        return channel_paths["preset_file"]

    def discover_channels(self) -> List[str]:
        """Tự động tìm tất cả channels trong ROOT_DIR"""
        channels = []
        
        # Kiểm tra ROOT_DIR tồn tại
        if not self.ROOT_DIR.exists():
            self.ROOT_DIR.mkdir(parents=True)
            return ["Channel4"]  # Channel mặc định
            
        # Lấy tất cả thư mục con trực tiếp của ROOT_DIR
        for item in self.ROOT_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                # Thêm channel vào danh sách và đảm bảo có đủ thư mục cần thiết
                channels.append(item.name)
                # Tạo các thư mục cần thiết nếu chưa có
                required_dirs = ["Scripts", "Working", "Completed", "Error", "Final", "Assets"]
                for subdir in required_dirs:
                    (item / subdir).mkdir(parents=True, exist_ok=True)
                    
        if not channels:
            channels = ["Channel4"]
            
        return channels

    def get_channels(self) -> List[str]:
        """Get list of all channels"""
        return self.CHANNELS

    def setup_template_channel(self):
        """Setup template channel với cấu trúc và preset mẫu"""
        # Ở đây ta vẫn làm việc với Path, sau đó mới convert khi cần trả về
        paths = self.get_channel_paths("_template")  # hàm này sẽ trả về dict[str, str]
        
        # Lúc này paths là dict[str, str], nên nếu cần mkdir / write_text,
        # ta chuyển thành Path tạm thởi:
        channel_dir = Path(paths["channel_dir"])
        config_file = Path(paths["config_file"])
        preset_file = Path(paths["preset_file"])
        
        voice_config = {
            "voice_settings": {
                "xtts_server_url": "http://localhost:5002",
                "speaker_voice": "EN_Ivy_Female",
                "language": "en",
                "temperature": 0.75,
                "length_penalty": 1,
                "repetition_penalty": 5,
                "top_k": 50,
                "top_p": 0.85,
                "speed": 1,
                "stream_chunk_size": 200,
                "enable_text_splitting": True,
                "max_sentence_length": 60,
                "enable_sentence_splitting": True,
                "enable_sentence_appending": True,
                "remove_diacritics": False,
                "output_format": "wav",
                "bitrate": "312k",
                "appended_silence": 200,
                "paragraph_silence": 200
            }
        }
        config_file.write_text(json.dumps(voice_config, indent=4, ensure_ascii=False), encoding='utf-8')
        
        video_preset = {
            "video_settings": {
                "preset_name": "1"
            },
            "voice_settings": {
                "xtts_server_url": "http://localhost:5002",
                "speaker_voice": "EN_Ivy_Female",
                "language": "en",
                "temperature": 0.75,
                "length_penalty": 1,
                "repetition_penalty": 5,
                "top_k": 50,
                "top_p": 0.85,
                "speed": 1,
                "stream_chunk_size": 200,
                "enable_text_splitting": True,
                "max_sentence_length": 60,
                "enable_sentence_splitting": True,
                "enable_sentence_appending": True,
                "remove_diacritics": False,
                "output_format": "wav",
                "bitrate": "312k",
                "appended_silence": 200,
                "paragraph_silence": 200
            }
        }
        preset_file.write_text(json.dumps(video_preset, indent=4, ensure_ascii=False), encoding='utf-8')
