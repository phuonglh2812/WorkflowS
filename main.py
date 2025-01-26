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
from workflows.workflow3.services.workflow_watcher import Workflow3Watcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Tạo event loop chung
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
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
        logger.info("Workflow2 watcher started successfully")
        
        # Khởi tạo và chạy workflow3 watcher
        logger.info("Starting Workflow3 watcher...")
        workflow3_watcher = Workflow3Watcher()
        workflow3_watcher.start_all_channels()
        logger.info("Workflow3 watcher started successfully")
        
        # Run event loop
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            # Cleanup
            workflow1_watcher.stop()
            workflow2_watcher.stop()
            workflow3_watcher.stop()
            
            # Close event loop
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
