# Hướng Dẫn Phát Triển

## 1. Tạo Workflow Mới

### 1.1 Cấu Trúc Thư Mục
```
/workflows/your_workflow/
    __init__.py
    config.py                # Cấu hình workflow
    /models/
        __init__.py
        task.py             # Models đặc thù
    /services/
        __init__.py
        processor.py        # Logic xử lý chính
        watcher.py          # File watcher
    /utils/
        __init__.py
        helpers.py          # Helper functions
```

### 1.2 Implement Base Classes

1. **Task Model**
```python
from common.models.base import BaseTask

class YourWorkflowTask(BaseTask):
    def __init__(self):
        self.required_fields = ['field1', 'field2']
        
    def validate(self):
        # Implement validation logic
        pass
        
    def to_dict(self):
        # Convert to dictionary
        pass
```

2. **Processor**
```python
from common.services.base_processor import BaseProcessor

class YourWorkflowProcessor(BaseProcessor):
    def __init__(self, config):
        self.config = config
        self.setup_services()
    
    async def process(self, context: dict):
        # Implement processing logic
        pass
        
    async def validate(self, context: dict):
        # Implement validation
        pass
        
    async def cleanup(self, context: dict):
        # Implement cleanup
        pass
```

3. **Watcher**
```python
from common.services.base_watcher import BaseWatcher

class YourWorkflowWatcher(BaseWatcher):
    def __init__(self, channel_name: str = None):
        self.paths = YourWorkflowPaths()
        watch_path = self.paths.get_channel_input_dir(channel_name)
        super().__init__(
            watch_path=watch_path,
            api_url="http://localhost:8000/your_workflow/process_file",
            channel_name=channel_name
        )
```

### 1.3 Cấu Hình

1. **Config Class**
```python
from pydantic import BaseModel

class YourWorkflowConfig(BaseModel):
    INPUT_FORMATS: list = ['txt', 'json']
    OUTPUT_FORMAT: str = 'mp4'
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    PROCESSING_OPTIONS: dict = {
        'option1': 'value1',
        'option2': 'value2'
    }
```

2. **Paths Config**
```python
from common.config.workflow_base_paths import WorkflowBasePaths

class YourWorkflowPaths(WorkflowBasePaths):
    def __init__(self):
        super().__init__("your_workflow")
        # Add custom paths
        self.CUSTOM_DIR = os.path.join(self.PROCESSING_DIR, "custom")
        os.makedirs(self.CUSTOM_DIR, exist_ok=True)
```

## 2. Đăng Ký Workflow

### 2.1 Trong main.py
```python
from workflows.your_workflow.services.processor import YourWorkflowProcessor
from workflows.your_workflow.config import YourWorkflowConfig

@app.on_event("startup")
async def startup():
    # Initialize config
    config = YourWorkflowConfig()
    
    # Create processor
    processor = YourWorkflowProcessor(config)
    
    # Register with job manager
    job_manager = await JobManager.get_instance()
    job_manager.register_workflow("your_workflow", processor)
```

### 2.2 Trong run_watchers.py
```python
from workflows.your_workflow.services.watcher import YourWorkflowWatcher

if __name__ == "__main__":
    watchers = [
        YourWorkflowWatcher(),  # Add your watcher
    ]
    
    for watcher in watchers:
        watcher.start()
```

## 3. Xử Lý Logic

### 3.1 Pre-processing
```python
async def pre_process(self, context: dict):
    """
    - Validate input
    - Prepare working directory
    - Initialize resources
    """
    pass
```

### 3.2 Main Processing
```python
async def process(self, context: dict):
    """
    - Step 1: Read input
    - Step 2: Transform data
    - Step 3: Generate output
    """
    pass
```

### 3.3 Post-processing
```python
async def post_process(self, context: dict):
    """
    - Cleanup temporary files
    - Move to output directory
    - Update database
    """
    pass
```

## 4. Error Handling

### 4.1 Exception Types
```python
class WorkflowError(Exception):
    """Base error for workflow"""
    pass

class ValidationError(WorkflowError):
    """Input validation error"""
    pass

class ProcessingError(WorkflowError):
    """Processing error"""
    pass
```

### 4.2 Error Handling
```python
try:
    await self.process(context)
except ValidationError as e:
    # Handle validation errors
    pass
except ProcessingError as e:
    # Handle processing errors
    pass
except Exception as e:
    # Handle unexpected errors
    pass
```

## 5. Testing

### 5.1 Unit Tests
```python
def test_processor():
    processor = YourWorkflowProcessor(config)
    result = await processor.process(test_context)
    assert result.status == 'success'
```

### 5.2 Integration Tests
```python
def test_workflow():
    # Test entire workflow
    pass
```

## 6. Monitoring

### 6.1 Logging
```python
from common.utils.logger import WorkflowLogger

logger = WorkflowLogger("your_workflow")
logger.info("Processing started")
logger.error("Error occurred", exc_info=True)
```

### 6.2 Metrics
```python
from common.utils.metrics import track_metric

track_metric("processing_time", value, workflow="your_workflow")
```

## 7. Best Practices

1. **Code Organization**
   - Keep related code together
   - Use meaningful names
   - Document complex logic

2. **Error Handling**
   - Always validate input
   - Log errors properly
   - Clean up resources

3. **Performance**
   - Monitor memory usage
   - Handle large files efficiently
   - Use async where appropriate

4. **Security**
   - Validate file types
   - Check file sizes
   - Sanitize input

5. **Maintenance**
   - Keep dependencies updated
   - Document changes
   - Write tests
