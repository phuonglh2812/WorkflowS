import os
import json
import httpx
import logging
import time
import shutil
from typing import Dict, Optional
from common.utils.base_service import BaseService, WorkflowContext
from ..config.workflow_paths import Workflow3Paths
import subprocess
import requests
import asyncio

logger = logging.getLogger(__name__)

class VoiceService(BaseService):
    def __init__(self, paths: Workflow3Paths):
        super().__init__()
        self.paths = paths
        self.api_url = str(paths.api_urls["voice_api"])     # Ép thành str
        self.xtts_url = str(paths.api_urls["xtts_api"])     # Ép thành str
        self.whisper_url = str(paths.api_urls["whisper_api"]) # Thêm whisper API URL
        self.pandora_dir = str(paths.PANDORA_DIR)           # Đảm bảo đây là str

    def _load_preset(self, channel_name: str) -> Optional[Dict]:
        """Load preset config từ thư mục channel"""
        channel_paths = self.paths.get_channel_paths(channel_name)
        preset_path = channel_paths["preset_file"]

        if not os.path.exists(preset_path):
            logger.warning(f"Preset file not found at {preset_path}")
            return None

        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                preset = json.load(f)
                logger.debug(f"Loaded preset from {preset_path}: {preset}")
                return preset.get('voice_settings', {})
        except Exception as e:
            logger.error(f"Failed to load preset: {str(e)}")
            return None

    def convert_to_str(self, data):
        """Đệ quy chuyển mọi Path-like hoặc object phức tạp thành str."""
        if isinstance(data, dict):
            return {k: self.convert_to_str(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.convert_to_str(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self.convert_to_str(item) for item in data)
        elif isinstance(data, os.PathLike):
            return str(data)
        else:
            return data

    async def process_hook(self, context: WorkflowContext) -> Dict:
        """Process hook file để tạo voice"""
        try:
            # Khởi tạo thuộc tính results nếu chưa có
            if not hasattr(context, 'results'):
                context.results = {}
            
            # Generate session name
            script_name = os.path.splitext(os.path.basename(context.file_path))[0]
            prefix = script_name.split('_Hook')[0]
            timestamp = str(int(time.time()))
            session_name = f"{script_name}_{timestamp}"
            
            # Load preset config
            voice_config = self._load_preset(context.channel_name)
            if not voice_config:
                logger.warning(f"No preset found for channel {context.channel_name}, using empty config")
                voice_config = {}
            
            # Dùng hàm đệ quy thay vì ép shallow
            voice_config = self.convert_to_str(voice_config)

            # Tạo request data
            request_data = {
                "source_file": str(context.file_path),
                "session_name": session_name,
                "xtts_server_url": self.xtts_url,
                **voice_config
            }

            # Cũng convert_to_str toàn bộ request_data
            request_data = self.convert_to_str(request_data)
            
            # Gọi voice API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/process_with_pandrator",
                    json=request_data,
                    timeout=1800
                )
                response.raise_for_status()
            
            logger.info("API call successful, waiting 10 seconds for files...")
            time.sleep(10)
            
            # Quan trọng: dùng self.pandora_dir đã,ep kiểu str
            pandrator_session = os.path.join(self.pandora_dir, "sessions", session_name)
            wav_source = os.path.join(pandrator_session, "final.wav")
            
            # Ép working_dir thành string
            channel_paths = self.paths.get_channel_paths(context.channel_name)
            working_dir = str(channel_paths["working_dir"])

            wav_target = os.path.join(working_dir, f"{prefix}_hook.wav")

            # Copy cả file wav
            shutil.copy2(wav_source, wav_target)

            return {
                'wav_file': wav_target,
            }
            
        except Exception as e:
            logger.error(f"Error processing hook file: {str(e)}")
            raise

    async def process(self, context: WorkflowContext) -> Dict:
        """Process KB file to generate voice"""
        logger.info(f"Starting voice process for KB file: {context.file_path}")

        try:
            # Khởi tạo thuộc tính results nếu chưa có
            if not hasattr(context, 'results'):
                context.results = {}
            
            # Get channel paths and prepare file paths
            channel_paths = self.paths.get_channel_paths(context.channel_name)
            logger.debug(f"Channel paths: {channel_paths}")

            script_name = os.path.splitext(os.path.basename(context.file_path))[0]
            prefix = script_name.split('_KB')[0]
            logger.debug(f"Script name: {script_name}, Prefix: {prefix}")

            # **Bổ sung: Đảm bảo working_dir là str**
            working_dir = str(channel_paths["working_dir"])

            # Define target paths ngay từ đầu
            wav_target = os.path.join(working_dir, f"{prefix}_audio.wav")
            srt_target = os.path.join(working_dir, f"{prefix}.srt")
            logger.debug(f"Target paths - WAV: {wav_target}, SRT: {srt_target}")

            # Khởi tạo voice_result ngay từ đầu
            voice_result = {
                'wav_file': wav_target,
                'srt_file': srt_target
            }
            logger.debug(f"Initialized voice_result: {voice_result}")

            # Generate session name
            timestamp = str(int(time.time()))
            session_name = f"{script_name}_{timestamp}"
            logger.debug(f"Generated session name: {session_name}")

            # Load preset config
            voice_config = self._load_preset(context.channel_name)
            if not voice_config:
                logger.warning(f"No preset found for channel {context.channel_name}, using empty config")
                voice_config = {}
            else:
                logger.debug(f"Loaded voice config: {voice_config}")

            # **Bổ sung: Đệ quy chuyển đổi Path thành str**
            voice_config = self.convert_to_str(voice_config)

            # Call voice API
            payload = {
                "source_file": str(context.file_path),
                "session_name": session_name,
                "xtts_server_url": self.xtts_url,
                **voice_config
            }

            # **Bổ sung: Đệ quy chuyển đổi toàn bộ payload thành str**
            payload = self.convert_to_str(payload)

            logger.debug(f"API payload: {payload}")

            logger.info(f"Calling voice API with session: {session_name}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/process_with_pandrator",
                    json=payload,
                    timeout=1800
                )
                response.raise_for_status()
                logger.debug(f"API response status: {response.status_code}")
                logger.debug(f"API response content: {response.text[:1000]}")  # Log first 1000 chars

            logger.info("API call successful, waiting 10 seconds for files...")
            time.sleep(10)

            # **Bổ sung: Chuyển đổi pandrator_session thành str**
            pandrator_session = os.path.join(self.pandora_dir, "sessions", session_name)
            wav_source = os.path.join(pandrator_session, "final.wav")
            logger.debug(f"Source paths - WAV: {wav_source}")

            # Copy files
            shutil.copy2(wav_source, wav_target)

            # Generate SRT using Whisper API
            srt_file = await self._generate_srt(wav_target, working_dir, prefix)
            voice_result['srt_file'] = srt_file

            return voice_result

        except Exception as e:
            logger.error(f"Error processing KB file: {str(e)}")
            raise

    async def _generate_srt(self, wav_file: str, output_dir: str, prefix: str) -> str:
        """Generate SRT file from WAV using Whisper API"""
        try:
            logger.info(f"Generating SRT for {wav_file}")
            
            # Prepare API request
            url = f"{self.whisper_url}/to_srt/"
            data = {
                "file_path": wav_file,
                "output_path": output_dir,
                "filename": prefix
            }
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json'
            }

            # Make API call with longer timeout
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, 
                    json=data, 
                    headers=headers,
                    timeout=1800  # 30 minutes
                )
                response.raise_for_status()
                
                # Log response
                result = response.json()
                logger.info(f"Whisper API response: {result}")
                
            # Wait for file to be created and check
            srt_file = os.path.join(output_dir, f"{prefix}.srt")
            max_retries = 30
            retry_count = 0
            
            while not os.path.exists(srt_file) and retry_count < max_retries:
                await asyncio.sleep(1)
                retry_count += 1
                
            if not os.path.exists(srt_file):
                raise Exception(f"SRT file not created after {max_retries} seconds: {srt_file}")
                
            logger.info(f"Successfully generated SRT file: {srt_file}")
            return srt_file
            
        except Exception as e:
            logger.error(f"Error generating SRT: {str(e)}")
            raise
