from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from common.database import get_db
from common.services.job_manager import JobManager
from common.models.job import JobPriority
from workflows.workflow1.main import process_workflow as workflow1_handler

app = FastAPI(
    title="Multi-Workflow System",
    description="System supporting multiple video generation workflows",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Khởi tạo Job Manager và đăng ký các workflow handlers
    job_manager = await JobManager.get_instance()
    job_manager.register_workflow_handler("workflow1", workflow1_handler)
    # Đăng ký thêm các workflow khác ở đây

@app.post("/api/jobs")
async def create_job(
    workflow_name: str,
    file_path: str,
    channel_name: str,
    priority: JobPriority = JobPriority.NORMAL,
    db: Session = Depends(get_db)
):
    job_manager = await JobManager.get_instance()
    job = await job_manager.add_job(db, workflow_name, file_path, channel_name, priority)
    return job.to_dict()

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job_manager = await JobManager.get_instance()
    job = await job_manager.get_job_status(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
