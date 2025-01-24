from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
from typing import Dict, Any, Optional
from common.models.job import Job, JobStatus, JobPriority
from common.database import get_db

class JobManager:
    _instance = None
    _lock = asyncio.Lock()
    _processing = False
    _workflow_handlers: Dict[str, Any] = {}

    def __init__(self):
        raise RuntimeError('Call get_instance() instead')

    @classmethod
    async def get_instance(cls):
        if not cls._instance:
            async with cls._lock:
                if not cls._instance:
                    cls._instance = object.__new__(cls)
                    cls._instance._workflow_handlers = {}
                    cls._instance._processing = False
        return cls._instance

    def register_workflow_handler(self, workflow_name: str, handler):
        """Đăng ký handler cho một workflow"""
        self._workflow_handlers[workflow_name] = handler

    async def add_job(self, db: Session, workflow_name: str, file_path: str, 
                     channel_name: str, priority: int = JobPriority.NORMAL) -> Job:
        """Thêm job mới vào queue"""
        # Tính processing_order dựa trên priority và thời gian
        processing_order = datetime.utcnow().timestamp() - (priority * 10000)
        
        job = Job(
            workflow_name=workflow_name,
            file_path=file_path,
            channel_name=channel_name,
            priority=priority,
            processing_order=processing_order
        )
        db.add(job)
        db.commit()

        # Bắt đầu xử lý queue nếu chưa chạy
        if not self._processing:
            asyncio.create_task(self._process_queue())

        return job

    async def _process_queue(self):
        """Xử lý các job trong queue theo thứ tự"""
        if self._processing:
            return

        self._processing = True
        try:
            while True:
                # Lấy DB session
                db = next(get_db())
                
                try:
                    # Lấy job tiếp theo cần xử lý
                    next_job = (
                        db.query(Job)
                        .filter(Job.status == JobStatus.PENDING)
                        .order_by(Job.processing_order)
                        .first()
                    )

                    if not next_job:
                        self._processing = False
                        return

                    # Cập nhật trạng thái job
                    next_job.status = JobStatus.PROCESSING
                    next_job.started_at = datetime.utcnow()
                    db.commit()

                    try:
                        # Lấy handler tương ứng với workflow
                        handler = self._workflow_handlers.get(next_job.workflow_name)
                        if not handler:
                            raise ValueError(f"No handler for workflow {next_job.workflow_name}")

                        # Xử lý job
                        result = await handler(next_job.file_path, next_job.channel_name)
                        
                        # Cập nhật kết quả
                        next_job.status = JobStatus.COMPLETED
                        next_job.completed_at = datetime.utcnow()
                        next_job.workflow_task_id = result.get("task_id")
                        db.commit()

                    except Exception as e:
                        next_job.status = JobStatus.ERROR
                        next_job.error_message = str(e)
                        next_job.completed_at = datetime.utcnow()
                        db.commit()
                        print(f"Error processing job {next_job.id}: {str(e)}")

                finally:
                    db.close()

                # Đợi một chút trước khi xử lý job tiếp theo
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in job queue processing: {str(e)}")
        finally:
            self._processing = False

    async def get_job_status(self, db: Session, job_id: int) -> Optional[Dict]:
        """Lấy trạng thái của một job"""
        job = db.query(Job).filter(Job.id == job_id).first()
        return job.to_dict() if job else None
