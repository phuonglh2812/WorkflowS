import os
import json
import httpx
import logging
import time
import shutil
import asyncio
import requests
from typing import Dict, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from common.utils.base_service import BaseService, WorkflowContext
from ..config.workflow_paths import Workflow2Paths

logger = logging.getLogger(__name__)

class VoiceService(BaseService):
    def __init__(self, paths: Workflow2Paths):
        super().__init__()
        self.paths = paths
        self.voice_api_url = paths.VOICE_API_URL
        self.xtts_url = paths.XTTS_SERVER_URL
        self.whisper_url = paths.WHISPER_SERVER_URL
        self.whisper_timeout = paths.WHISPER_API_TIMEOUT
        self.pandora_dir = str(paths.PANDORA_DIR)
        
        # Setup session with retry mechanism
        self.session = requests.Session()
        retries = Retry(
            total=5,  # số lần retry tối đa
            backoff_factor=1,  # thời gian chờ giữa các lần retry (1s, 2s, 4s, 8s, 16s)
            status_forcelist=[500, 502, 503, 504],  # retry với các status code này
            allowed_methods=["POST", "GET"]  # cho phép retry với các method này
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retries))

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
                return preset
        except Exception as e:
            logger.error(f"Failed to load preset: {str(e)}")
            return None

    async def _generate_tts(self, text_file: str, output_dir: str, output_filename: str, voice_config: Dict) -> str:
        """Generate TTS using Pandrator API"""
        try:
            # Generate session name
            script_name = os.path.splitext(os.path.basename(text_file))[0]
            timestamp = str(int(time.time()))
            session_name = f"{script_name}_{timestamp}"
            
            # Prepare request data
            request_data = {
                "source_file": str(text_file),
                "session_name": session_name,
                "xtts_server_url": self.xtts_url,
                **voice_config
            }

            # Call voice API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.voice_api_url}/process_with_pandrator",
                    json=request_data,
                    timeout=1800
                )
                response.raise_for_status()
            
            logger.info("API call successful, waiting 10 seconds for files...")
            time.sleep(10)
            
            # Get the generated wav file
            pandrator_session = os.path.join(self.pandora_dir, "sessions", session_name)
            wav_source = os.path.join(pandrator_session, "final.wav")
            
            if not os.path.exists(wav_source):
                raise FileNotFoundError(f"Generated WAV file not found at {wav_source}")
            
            # Move to target location
            wav_target = os.path.join(output_dir, output_filename)
            shutil.copy2(wav_source, wav_target)
            
            return wav_target

        except Exception as e:
            logger.error(f"Error generating TTS: {str(e)}")
            raise

    async def _generate_srt(self, wav_file: str, text_content: str, channel_name: str = None) -> str:
        """Generate SRT using whisper API with configurable options"""
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                # Get channel config if available
                channel_config = {}
                if channel_name:
                    preset = self._load_preset(channel_name)
                    if preset:
                        channel_config = preset.get('whisper_settings', {})

                # Prepare output directory and filename
                output_dir = os.path.dirname(wav_file)
                filename = os.path.splitext(os.path.basename(wav_file))[0]

                # Prepare request data
                data = {
                    "file_path": wav_file,
                    "output_path": output_dir,
                    "filename": filename,
                    "words_per_segment": channel_config.get('words_per_segment', 2),
                    "max_chars": channel_config.get('max_chars', 80)
                }

                # Call whisper API to generate SRT using session with retry
                response = self.session.post(
                    f"{self.whisper_url}/to_srt/",
                    json=data,
                    timeout=self.whisper_timeout
                )
                response.raise_for_status()
                
                # Get result
                result = response.json()
                if result.get('status') != 'success':
                    raise Exception(f"Whisper API error: {result.get('message', 'Unknown error')}")

                # Get the SRT file path
                srt_file = os.path.join(output_dir, f"{filename}.srt")
                if not os.path.exists(srt_file):
                    raise FileNotFoundError(f"Generated SRT file not found at {srt_file}")

                return srt_file

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries exceeded. Please check if Whisper server is running.")
                    raise
            except Exception as e:
                logger.error(f"Error generating SRT: {str(e)}")
                raise

    async def process_hook(self, context: WorkflowContext) -> Dict:
        """Process hook file"""
        try:
            logger.info(f"Starting voice process for KB file: {context.file_path}")
            
            # Initialize results if not exists
            if not hasattr(context, 'results'):
                context.results = {}
            
            # Get file paths and configs
            script_name = os.path.splitext(os.path.basename(context.file_path))[0]
            prefix = script_name.split('_Hook')[0] if '_Hook' in script_name else script_name.split('_KB')[0]
            
            channel_paths = self.paths.get_channel_paths(context.channel_name)
            working_dir = str(channel_paths["working_dir"])
            
            # Load voice config
            preset = self._load_preset(context.channel_name)
            if not preset:
                logger.warning(f"No preset found for channel {context.channel_name}, using default config")
                voice_config = {}
            else:
                voice_config = preset.get('voice_settings', {})
            
            # Generate TTS
            wav_target = f"{prefix}_hook.wav" if '_Hook' in script_name else f"{prefix}_audio.wav"
            wav_file = await self._generate_tts(
                text_file=context.file_path,
                output_dir=working_dir,
                output_filename=wav_target,
                voice_config=voice_config
            )
            
            # Only generate SRT for _KB files, not _hook files
            srt_file = None
            if '_KB' in script_name:  # Only for main audio files
                with open(context.file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                srt_file = await self._generate_srt(wav_file, text_content, context.channel_name)

            return {
                'wav_file': wav_file,
                'srt_file': srt_file
            }

        except Exception as e:
            logger.error(f"Error processing KB file: {str(e)}")
            raise

    async def process(self, context: WorkflowContext) -> Dict:
        """Implement abstract method from BaseService"""
        return await self.process_hook(context)
