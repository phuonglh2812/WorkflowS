import time
import signal
import sys
import logging
import os
from pathlib import Path
from workflows.workflow1.services.workflow_watcher import Workflow1Watcher
from workflows.workflow2.services.workflow_watcher import Workflow2Watcher

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    logger.info("Stopping all watchers...")
    for watcher in watchers:
        watcher.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize watchers
    watchers = []
    
    # Add Workflow1 watcher
    workflow1_watcher = Workflow1Watcher()
    watchers.append(workflow1_watcher)
    
    # Add Workflow2 watcher
    try:
        workflow2_watcher = Workflow2Watcher()
        watchers.append(workflow2_watcher)
    except Exception as e:
        logger.error(f"Error initializing Workflow2Watcher: {str(e)}")

    # Start all watchers
    logger.info("Starting all watchers...")
    for watcher in watchers:
        try:
            watcher.start()
        except Exception as e:
            logger.error(f"Error starting watcher: {str(e)}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping all watchers...")
        for watcher in watchers:
            watcher.stop()
