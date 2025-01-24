import asyncio
from typing import List
from common.models.job import Job
from common.utils.base_service import BaseService, WorkflowContext

class BaseWorkflow:
    """Base class cho các workflow"""
    
    def __init__(self, paths):
        self.paths = paths
        self.services: List[BaseService] = []
        
    def add_service(self, service: BaseService):
        """Thêm một service vào workflow"""
        self.services.append(service)
        
    async def process(self, context: WorkflowContext):
        """Process một context qua tất cả các service"""
        for service in self.services:
            # Gọi service và lưu kết quả vào context
            result = await service.process(context)
            if result:
                if not hasattr(context, 'results'):
                    context.results = {}
                context.results[service.__class__.__name__] = result
                
        return context.results
