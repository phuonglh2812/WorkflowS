import os
import json
import httpx
import uuid
import shutil
import time
from typing import Dict, Optional
from common.utils.base_service import BaseService, WorkflowContext
from ..config.workflow_paths import Workflow1Paths
import traceback

class VoiceService(BaseService):
    def __init__(self, paths: Workflow1Paths):
        super().__init__()
        self.paths = paths
        self.api_url = paths.api_urls["voice_api"]
        self.xtts_url = paths.api_urls["xtts_api"]

    def _load_preset(self, channel_name: str) -> Optional[Dict]:
        """Load preset config từ thư mục channel"""
        preset_path = self.paths.get_preset_path(channel_name)
        
        if not os.path.exists(preset_path):
            self.logger.error(f"Preset not found at {preset_path}")
            return None
            
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset = json.load(f)
                return preset.get('voice_settings', {})
        except Exception as e:
            self.logger.error(f"Failed to load preset: {str(e)}")
            return None

    async def process(self, context: WorkflowContext) -> Dict:
        """Process voice with timeout 30 minutes"""
        self.logger.info(f"Starting voice process for file: {context.file_path}")
        
        try:
            # Get channel paths and prepare file paths
            channel_paths = self.paths.get_channel_paths(context.channel_name)
            self.logger.debug(f"Channel paths: {channel_paths}")
            
            script_name = os.path.splitext(os.path.basename(context.file_path))[0]
            prefix = script_name.split('_KB')[0]
            self.logger.debug(f"Script name: {script_name}, Prefix: {prefix}")
            
            # Define target paths ngay từ đầu
            wav_target = os.path.join(channel_paths["working_dir"], f"{prefix}_audio.wav")
            srt_target = os.path.join(channel_paths["working_dir"], f"{prefix}.srt")
            self.logger.debug(f"Target paths - WAV: {wav_target}, SRT: {srt_target}")
            
            # Khởi tạo voice_result ngay từ đầu
            voice_result = {
                'wav_file': wav_target,
                'srt_file': srt_target
            }
            self.logger.debug(f"Initialized voice_result: {voice_result}")
            
            try:
                # Generate session name
                session_name = f"{script_name}_{uuid.uuid4().hex}"
                self.logger.debug(f"Generated session name: {session_name}")
                
                # Load preset config
                voice_config = self._load_preset(context.channel_name)
                if not voice_config:
                    self.logger.warning(f"No preset found for channel {context.channel_name}, using empty config")
                    voice_config = {}
                else:
                    self.logger.debug(f"Loaded voice config: {voice_config}")
                    
                # Call voice API
                payload = {
                    "source_file": context.file_path,
                    "session_name": session_name,
                    "xtts_server_url": self.xtts_url,
                    **voice_config
                }
                self.logger.debug(f"API payload: {payload}")
                
                self.logger.info(f"Calling voice API with session: {session_name}")
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.api_url}/process_with_pandrator",
                        json=payload,
                        timeout=1800
                    )
                    self.logger.debug(f"API response status: {response.status_code}")
                    self.logger.debug(f"API response content: {response.text[:1000]}")  # Log first 1000 chars

                self.logger.info("API call successful, waiting 10 seconds for files...")
                time.sleep(10)
                
                # Copy files from session to working dir
                pandrator_session = os.path.join(self.paths.PANDORA_DIR, "sessions", session_name)
                wav_source = os.path.join(pandrator_session, "final.wav")
                srt_source = os.path.join(pandrator_session, "final.srt")
                self.logger.debug(f"Source paths - WAV: {wav_source}, SRT: {srt_source}")
                
                # Đảm bảo thư mục đích tồn tại
                os.makedirs(os.path.dirname(wav_target), exist_ok=True)
                os.makedirs(os.path.dirname(srt_target), exist_ok=True)
                self.logger.debug("Created target directories")
                
                # Copy và đổi tên file
                if os.path.exists(wav_source):
                    self.logger.debug(f"Found WAV file at {wav_source}")
                    shutil.copy2(wav_source, wav_target)
                    self.logger.info(f"Copied WAV file to {wav_target}")
                else:
                    self.logger.error(f"WAV file not found at {wav_source}")
                    
                if os.path.exists(srt_source):
                    self.logger.debug(f"Found SRT file at {srt_source}")
                    shutil.copy2(srt_source, srt_target)
                    self.logger.info(f"Copied SRT file to {srt_target}")
                else:
                    self.logger.error(f"SRT file not found at {srt_source}")
                
            except Exception as e:
                self.logger.error(f"Error during voice processing: {str(e)}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                raise
                
        except Exception as e:
            self.logger.error(f"Error in voice processing: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise
            
        self.logger.info(f"Voice processing completed. Returning: {voice_result}")
        return voice_result
