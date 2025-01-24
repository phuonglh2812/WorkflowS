from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
import logging
from common.database import get_db
from common.services.job_manager import JobManager
from common.models.job import JobPriority
from .services.workflow_watcher import Workflow1Watcher
from .workflow import Workflow1

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Workflow1 Service",
    description="Service for handling Workflow1 video generation",
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

# Global watcher
watcher = None

@app.on_event("startup")
async def startup_event():
    global watcher
    try:
        # Start workflow1 watcher
        workflow = Workflow1()
        watcher = Workflow1Watcher(workflow)
        watcher.start()
        logger.info("Started Workflow1 watcher")
    except Exception as e:
        logger.error(f"Error starting Workflow1 watcher: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    global watcher
    if watcher:
        try:
            watcher.stop()
            logger.info("Stopped Workflow1 watcher")
        except Exception as e:
            logger.error(f"Error stopping Workflow1 watcher: {str(e)}")

@app.post("/jobs/")
async def create_job(
    file_path: str,
    channel_name: str,
    priority: JobPriority = JobPriority.NORMAL,
    db: Session = Depends(get_db)
):
    job_manager = await JobManager.get_instance()
    return await job_manager.create_job(
        workflow_name="workflow1",
        file_path=file_path,
        channel_name=channel_name,
        priority=priority,
        db=db
    )

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job_manager = await JobManager.get_instance()
    return await job_manager.get_job_status(job_id, db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("workflows.workflow1.main:app", host="0.0.0.0", port=8000, reload=True)
