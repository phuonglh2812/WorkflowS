import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import httpx
from typing import Optional

class BaseWatcherHandler(FileSystemEventHandler):
    def __init__(self, api_url: str, channel_name: Optional[str] = None):
        self.api_url = api_url
        self.channel_name = channel_name
        
    async def process_file(self, file_path: str):
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                payload = {
                    "file_path": file_path,
                    "channel_name": self.channel_name or os.path.basename(os.path.dirname(file_path))
                }
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            return None

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.txt'):
            import asyncio
            asyncio.create_task(self.process_file(event.src_path))

class BaseWatcher:
    def __init__(self, watch_path: str, api_url: str, channel_name: Optional[str] = None):
        self.watch_path = watch_path
        self.api_url = api_url
        self.channel_name = channel_name
        self.observer = Observer()

    def start(self):
        """Start watching the directory"""
        event_handler = BaseWatcherHandler(self.api_url, self.channel_name)
        self.observer.schedule(event_handler, self.watch_path, recursive=False)
        self.observer.start()
        print(f"Started watching {self.watch_path}")

    def stop(self):
        """Stop watching the directory"""
        self.observer.stop()
        self.observer.join()
        print(f"Stopped watching {self.watch_path}")
