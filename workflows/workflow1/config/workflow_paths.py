import os
import json
from pathlib import Path
from typing import Dict, List
from common.config.base_paths import BasePathConfig

class Workflow1Paths(BasePathConfig):
    def __init__(self):
        # Khởi tạo base class trước
        super().__init__(workflow_name="workflow1")
        
        # Khởi tạo các đường dẫn
        self.ROOT_DIR = Path(os.getenv("WORKFLOW_ROOT", "D:/AutomateWorkFlow/workflow1"))
        self.PANDORA_DIR = Path(os.getenv("PANDORA_DIR", "D:/AutomateWorkFlow/WorkflowFile/Pandrator"))
        self.VIDEO_DIR = Path(os.getenv("VIDEO_DIR", "D:/AutomateWorkFlow/WorkflowFile/VideoMakerS_Files"))
        self.FINAL_DIR = Path(os.getenv("FINAL_DIR", "D:/AutomateWorkFlow/WorkflowFile/VideoMakerS_Files/final"))
        
        # Tạo template channel
        self.setup_template_channel()

    def get_channel_paths(self, channel_name: str) -> Dict[str, Path]:
        """Get all paths for a specific channel"""
        channel_base = self.ROOT_DIR / channel_name
        
        paths = {
            # Thư mục chính
            "channel_dir": channel_base,
            "scripts_dir": channel_base / "Scripts",
            "working_dir": channel_base / "Working",
            "completed_dir": channel_base / "Completed",
            "error_dir": channel_base / "Error",
            "final_dir": channel_base / "Final",
            
            # Thư mục assets
            "assets_dir": channel_base / "Assets",
            "overlay1_dir": channel_base / "Assets" / "Overlay1",
            "overlay2_dir": channel_base / "Assets" / "Overlay2",
            
            # Config files
            "config_file": channel_base / "config.json",
            "preset_file": channel_base / "preset.json",
            
            # Video service paths - final output
            "video_final": self.FINAL_DIR
        }
        
        # Tạo các thư mục nếu chưa tồn tại
        for path in paths.values():
            if not str(path).endswith('.json'):
                path.mkdir(parents=True, exist_ok=True)
                
        return paths

    def get_pandora_session_paths(self, session_name: str) -> Dict[str, Path]:
        """Get paths for a specific Pandora session"""
        session_base = self.PANDORA_DIR / "sessions" / session_name
        
        paths = {
            "session_dir": session_base,
            "wav_file": session_base / "final.wav",
            "srt_file": session_base / "final.srt"
        }
        
        session_base.mkdir(parents=True, exist_ok=True)
        return paths

    def get_working_file_paths(self, channel_name: str, script_name: str) -> Dict[str, Path]:
        """Get paths for working files in channel's Working directory"""
        channel_paths = self.get_channel_paths(channel_name)
        base_name = Path(script_name).stem
        
        paths = {
            "wav_file": channel_paths["working_dir"] / f"{base_name}.wav",
            "srt_file": channel_paths["working_dir"] / f"{base_name}.srt"
        }
        
        return paths

    def get_preset_path(self, channel_name: str) -> Path:
        """Get path to preset file"""
        channel_paths = self.get_channel_paths(channel_name)
        return channel_paths["preset_file"]

    def get_channels(self) -> List[str]:
        """Get list of all channels"""
        if not os.path.exists(self.ROOT_DIR):
            return []
            
        channels = []
        for item in os.listdir(self.ROOT_DIR):
            if os.path.isdir(os.path.join(self.ROOT_DIR, item)) and not item.startswith('_'):
                channels.append(item)
                
        return channels

    def setup_template_channel(self):
        """Setup template channel với cấu trúc và preset mẫu"""
        # Tạo cấu trúc thư mục
        paths = self.get_channel_paths("_template")
        
        # Tạo voice config
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
        
        paths["config_file"].write_text(json.dumps(voice_config, indent=4, ensure_ascii=False), encoding='utf-8')
        
        # Tạo video preset
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
        
        paths["preset_file"].write_text(json.dumps(video_preset, indent=4, ensure_ascii=False), encoding='utf-8')
            
        # Tạo README.md với hướng dẫn
        readme_content = """# Template Channel

Đây là template channel với cấu trúc thư mục và config mẫu.
Copy toàn bộ thư mục này và đổi tên thành tên channel mới để bắt đầu.

## Cấu trúc thư mục:
- Scripts/: Chứa các file script cần xử lý
- Working/: Chứa các file đang được xử lý
- Completed/: Chứa các file đã xử lý xong
- Error/: Chứa các file xử lý lỗi
- Final/: Chứa các video đầu ra
- Assets/
  - Overlay1/: Chứa logo cố định (logo.png)
  - Overlay2/: Chứa các overlay ngẫu nhiên
- config.json: Cấu hình cho voice service
- preset.json: Cấu hình cho video service

## Config files:
1. config.json - Voice settings:
```json
{
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
        "enable_text_splitting": true,
        "max_sentence_length": 60,
        "enable_sentence_splitting": true,
        "enable_sentence_appending": true,
        "remove_diacritics": false,
        "output_format": "wav",
        "bitrate": "312k",
        "appended_silence": 200,
        "paragraph_silence": 200
    }
}
```

2. preset.json - Video settings:
```json
{
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
        "enable_text_splitting": true,
        "max_sentence_length": 60,
        "enable_sentence_splitting": true,
        "enable_sentence_appending": true,
        "remove_diacritics": false,
        "output_format": "wav",
        "bitrate": "312k",
        "appended_silence": 200,
        "paragraph_silence": 200
    }
}
```

## Quy trình làm việc:
1. Copy template channel này thành channel mới
2. Chỉnh sửa config.json và preset.json theo nhu cầu
3. Thêm logo vào Overlay1/logo.png
4. Thêm các overlay vào Overlay2/
5. Đặt file script vào Scripts/ để bắt đầu xử lý
"""
        
        readme_path = paths["channel_dir"] / "README.md"
        readme_path.write_text(readme_content, encoding='utf-8')
            
        # Tạo file logo.png mẫu trong Overlay1
        logo_path = paths["overlay1_dir"] / "logo.png"
        if not logo_path.exists():
            logo_path.touch()
                
        # Tạo một file overlay mẫu trong Overlay2
        overlay_path = paths["overlay2_dir"] / "sample_overlay.png"
        if not overlay_path.exists():
            overlay_path.touch()
        
        print(f"Created template channel at: {paths['channel_dir']}")
        print("Copy this template and rename it to create new channels")
