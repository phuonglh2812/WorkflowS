from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime, Float
import enum
from datetime import datetime
from common.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

class JobPriority(int, enum.Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    workflow_name = Column(String, nullable=False)
    workflow_task_id = Column(Integer, nullable=True)  # ID của task trong workflow tương ứng
    file_path = Column(String, nullable=False)
    channel_name = Column(String, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    priority = Column(Integer, default=JobPriority.NORMAL)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_order = Column(Float, nullable=True)  # Để sắp xếp thứ tự xử lý

    def to_dict(self):
        return {
            "id": self.id,
            "workflow_name": self.workflow_name,
            "workflow_task_id": self.workflow_task_id,
            "file_path": self.file_path,
            "channel_name": self.channel_name,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
