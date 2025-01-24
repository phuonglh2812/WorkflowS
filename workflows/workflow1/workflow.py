import os
import logging
from typing import Dict, List, Optional
from common.utils.base_workflow import BaseWorkflow
from common.utils.base_service import WorkflowContext
from .config.workflow_paths import Workflow1Paths
from .services.voice_service import VoiceService
from .services.video_service import VideoService

logger = logging.getLogger(__name__)

class Workflow1(BaseWorkflow):
    def __init__(self, paths: Optional[Workflow1Paths] = None):
        self.paths = paths or Workflow1Paths()
        super().__init__(self.paths)
        self.logger = logging.getLogger(__name__)
        
        # Khởi tạo các services
        self.voice_service = VoiceService(self.paths)
        self.video_service = VideoService(self.paths)

    def _get_paired_files(self, channel_name: str) -> List[Dict[str, str]]:
        """Tìm các cặp file hook và kb trong thư mục script"""
        channel_paths = self.paths.get_channel_paths(channel_name)
        script_dir = channel_paths["scripts_dir"]
        
        # Lấy danh sách tất cả file txt trong thư mục script
        txt_files = [f for f in os.listdir(script_dir) if f.endswith('.txt')]
        
        # Tạo dictionary để lưu các cặp file
        file_pairs = {}
        
        for file_name in txt_files:
            # Lấy prefix từ tên file
            if '_hook.txt' in file_name:
                prefix = file_name.split('_hook.txt')[0]
                if prefix not in file_pairs:
                    file_pairs[prefix] = {'hook': None, 'kb': None}
                file_pairs[prefix]['hook'] = os.path.join(script_dir, file_name)
            elif '_KB.txt' in file_name:
                prefix = file_name.split('_KB.txt')[0]
                if prefix not in file_pairs:
                    file_pairs[prefix] = {'hook': None, 'kb': None}
                file_pairs[prefix]['kb'] = os.path.join(script_dir, file_name)
        
        # Chỉ giữ lại các cặp file đầy đủ
        complete_pairs = []
        for prefix, pair in file_pairs.items():
            if pair['hook'] and pair['kb']:
                complete_pairs.append(pair)
                
        return complete_pairs

    async def process_hook(self, context: WorkflowContext) -> Dict:
        """Xử lý file hook.txt"""
        try:
            # Đọc nội dung file
            with open(context.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Tạo thumbnail và hook overlay
            thumbnail_path = self.thumbnail_service.create_thumbnail(context.channel_name, content)
            hook_path = self.thumbnail_service.create_hook(context.channel_name, content)
            
            # Tạo voice
            voice_result = await self.voice_service.process_hook(context)
            
            return {
                'thumbnail_path': thumbnail_path,
                'hook_path': hook_path,
                'voice_result': voice_result
            }
            
        except Exception as e:
            self.logger.error(f"Error processing hook file: {str(e)}")
            raise

    async def process_kb(self, context: WorkflowContext) -> Dict:
        """Xử lý file KB.txt"""
        try:
            # Tạo voice
            voice_result = await self.voice_service.process(context)
            
            # Lưu voice result vào context
            if not hasattr(context, 'results'):
                context.results = {}
            context.results['VoiceService'] = voice_result
            
            # Tạo video
            video_result = await self.video_service.process(context)
            
            return {
                'voice_result': voice_result,
                'video_result': video_result
            }
            
        except Exception as e:
            self.logger.error(f"Error processing KB file: {str(e)}")
            raise

    async def process(self, context: WorkflowContext) -> Dict:
        """Process a single file based on its type"""
        try:
            file_name = os.path.basename(context.file_path)
            
            if '_hook.txt' in file_name:
                return await self.process_hook(context)
            elif '_KB.txt' in file_name:
                return await self.process_kb(context)
            else:
                raise ValueError(f"Unknown file type: {file_name}")
                
        except Exception as e:
            self.logger.error(f"Error processing file {context.file_path}: {str(e)}")
            raise
