import time
import signal
import sys
from workflows.workflow1.services.workflow_watcher import Workflow1Watcher

def signal_handler(signum, frame):
    print("\nStopping all watchers...")
    for watcher in watchers:
        watcher.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize watchers
    watchers = [
        Workflow1Watcher(),  # Add more watchers here for other workflows
    ]

    # Start all watchers
    for watcher in watchers:
        watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all watchers...")
        for watcher in watchers:
            watcher.stop()
