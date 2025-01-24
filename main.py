import os
import sys
import asyncio
import logging
from pathlib import Path

# Add root path to sys.path
ROOT_PATH = str(Path(__file__).parent)
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from workflows.workflow1.workflow import Workflow1
from workflows.workflow1.config.workflow_paths import Workflow1Paths
from workflows.workflow1.services.workflow_watcher import Workflow1Watcher
from workflows.workflow2.services.workflow_watcher import Workflow2Watcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Khởi tạo và chạy workflow1 watcher
        logger.info("Starting Workflow1 watcher...")
        workflow1_paths = Workflow1Paths()
        workflow1 = Workflow1(workflow1_paths)
        workflow1_watcher = Workflow1Watcher(workflow1)
        workflow1_watcher.start()
        logger.info("Workflow1 watcher started successfully")
        
        # Khởi tạo và chạy workflow2 watcher
        logger.info("Starting Workflow2 watcher...")
        workflow2_watcher = Workflow2Watcher()
        workflow2_watcher.start_all_channels()
        workflow2_watcher.run_event_loop()
        logger.info("Workflow2 watcher started successfully")
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping...")
        workflow1_watcher.stop()
        workflow2_watcher.stop()
    except Exception as e:
        logger.error(f"Error running workflow watchers: {str(e)}")
        raise
