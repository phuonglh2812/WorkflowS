import os
import shutil
import logging
import traceback
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from common.utils.base_service import WorkflowContext
from common.database import get_db
from common.utils.base_workflow import BaseWorkflow
from .config.workflow_paths import Workflow1Paths
from .services.voice_service import VoiceService
from .services.video_service import VideoService
from .services.workflow_watcher import Workflow1Watcher
from .models.workflow import Workflow1Task, WorkflowStatus

# Cấu hình logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Khởi tạo FastAPI app cho workflow1
app = FastAPI(
    title="Video Generation Workflow",
    description="API for processing scripts into videos",
    version="1.0.0"
)

# Khởi tạo paths và services
paths = Workflow1Paths()
voice_service = VoiceService(paths)
video_service = VideoService(paths)

# Khởi tạo workflow
workflow = BaseWorkflow(paths)
workflow.add_service(voice_service)
workflow.add_service(video_service)

# Khởi tạo watcher
watcher = Workflow1Watcher(workflow)

@app.on_event("startup")
async def startup_event():
    """Khởi động các watcher khi startup"""
    # Lấy danh sách các channel (trừ _template)
    channels = [d for d in os.listdir(paths.CHANNELS_DIR) 
               if os.path.isdir(os.path.join(paths.CHANNELS_DIR, d)) 
               and not d.startswith('_')]
    
    # Watch mỗi channel
    for channel in channels:
        watcher.watch_channel(channel)
    
    print(f"Started watchers for channels: {', '.join(channels)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Dừng các watcher khi shutdown"""
    watcher.stop()
    print("Stopped all watchers")

async def process_workflow(context: WorkflowContext, db: Session):
    """
    Xử lý workflow với database tracking
    """
    # Create workflow task
    task = Workflow1Task(
        file_name=os.path.basename(context.file_path),
        file_path=context.file_path,
        channel_name=context.channel_name
    )
    db.add(task)
    db.commit()
    
    try:
        # Bước 1: Xử lý Voice
        task.status = WorkflowStatus.VOICE_PROCESSING
        db.commit()
        
        try:
            logger.info(f"Starting voice processing for file: {context.file_path}")
            voice_result = await voice_service.process(context)
            logger.debug(f"Voice result: {voice_result}")
            
            if not isinstance(voice_result, dict):
                logger.error(f"Invalid voice_result type: {type(voice_result)}")
                raise ValueError(f"Invalid voice_result type: {type(voice_result)}")
                
            logger.debug(f"Accessing wav_file from voice_result: {voice_result.get('wav_file')}")
            logger.debug(f"Accessing srt_file from voice_result: {voice_result.get('srt_file')}")
            
            task.audio_path = voice_result['wav_file']
            task.srt_path = voice_result['srt_file']
            task.status = WorkflowStatus.VOICE_DONE
            db.commit()
            logger.info("Voice processing completed successfully")
            
        except Exception as e:
            logger.error(f"Voice processing failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            task.status = WorkflowStatus.ERROR
            task.error_message = str(e)
            db.commit()
            raise
        
        # Bước 2: Xử lý Video
        task.status = WorkflowStatus.VIDEO_PROCESSING
        db.commit()
        
        video_result = await video_service.process(context)
        
        # Di chuyển video vào thư mục final
        channel_paths = paths.get_channel_paths(context.channel_name)
        final_path = os.path.join(channel_paths["final_dir"], f"{os.path.splitext(os.path.basename(context.file_path))[0]}.mp4")
        shutil.move(video_result['output_path'], final_path)
        
        task.status = WorkflowStatus.COMPLETED
        task.video_path = final_path
        db.commit()
        
        return {
            "status": "success",
            "task_id": task.id,
            "message": f"Processed {context.file_path} successfully"
        }
        
    except Exception as e:
        logger.error(f"Error processing file {context.file_path}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        task.status = WorkflowStatus.ERROR
        task.error_message = str(e)
        db.commit()
        raise e

@app.post("/process_file")
async def process_file(
    file_path: str,
    channel_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    context = WorkflowContext(file_path=file_path, channel_name=channel_name)
    background_tasks.add_task(process_workflow, context, db)
    return {"message": "Processing started", "file_path": file_path}

@app.get("/status/{task_id}")
async def get_status(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Workflow1Task).filter(Workflow1Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
