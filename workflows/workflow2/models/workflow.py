from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime
import enum
from datetime import datetime
from common.database import Base

class WorkflowStatus(str, enum.Enum):
    PENDING = "PENDING"
    VOICE_PROCESSING = "VOICE_PROCESSING"
    VOICE_DONE = "VOICE_DONE"
    VIDEO_PROCESSING = "VIDEO_PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

class Workflow1Task(Base):
    __tablename__ = "workflow1_tasks"

    id = Column(Integer, primary_key=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    channel_name = Column(String, nullable=False)
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING)
    error_message = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    srt_path = Column(String, nullable=True)
    video_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "file_name": self.file_name,
            "channel_name": self.channel_name,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
