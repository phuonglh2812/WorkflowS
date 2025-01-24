# Multi-Workflow System

Hệ thống xử lý nhiều workflow với quản lý job queue tập trung.

## 1. Cấu Trúc Thư Mục

```
/project_root/
    /common/                     # Các module dùng chung
        /config/                # Cấu hình hệ thống
        /models/               # Base models và job models
        /services/            # Các services chung
        /utils/              # Utility functions
    
    /data/                  # Thư mục data
        /{workflow_name}/   # Mỗi workflow một thư mục
            /input/        # Files đầu vào
            /processing/  # Files đang xử lý
            /output/     # Files đã xử lý xong
            /archive/   # Files lưu trữ
            /error/    # Files lỗi

    /workflows/          # Các workflow cụ thể
        /{workflow_name}/ # Mỗi workflow một thư mục
```

## 2. Luồng Xử Lý

### 2.1 Khởi Động Hệ Thống
1. Load cấu hình từ file .env và config files
2. Khởi tạo database connection
3. Khởi tạo JobManager
4. Đăng ký các workflow handlers
5. Start FastAPI server
6. Start các watchers

### 2.2 Xử Lý Job
1. **File Detection**
   - Watcher phát hiện file mới trong thư mục input
   - Gửi thông tin file đến API endpoint

2. **Job Creation**
   - API nhận request
   - Tạo job mới trong database
   - Thêm vào job queue

3. **Queue Processing**
   - JobManager xử lý queue theo thứ tự ưu tiên
   - Chỉ xử lý một job tại một thời điểm
   - Theo dõi và cập nhật trạng thái job

4. **Workflow Processing**
   - Mỗi workflow có processor riêng
   - Xử lý file theo logic của workflow
   - Cập nhật tiến trình vào database

5. **Output Handling**
   - Lưu kết quả vào thư mục output
   - Di chuyển input file vào archive
   - Cập nhật trạng thái job thành completed

### 2.3 Xử Lý Lỗi
- Ghi log chi tiết
- Di chuyển file lỗi vào thư mục error
- Cập nhật trạng thái và thông tin lỗi
- Tiếp tục xử lý job tiếp theo

## 3. Components Chính

### 3.1 Job Manager
- Singleton class quản lý job queue
- Đăng ký và quản lý các workflow
- Xử lý job theo priority
- Theo dõi trạng thái các job

### 3.2 Base Classes
1. **BaseTask**
   - Base class cho task models
   - Định nghĩa interface chung
   - Xử lý validation

2. **BaseProcessor**
   - Base class cho workflow processors
   - Định nghĩa các methods chuẩn
   - Xử lý lỗi và cleanup

3. **BaseWatcher**
   - Base class cho file watchers
   - Theo dõi thư mục input
   - Xử lý file events

### 3.3 Database Models
1. **Job Model**
   - ID và metadata
   - Workflow information
   - Status và timestamps
   - Error tracking

2. **Workflow Models**
   - Specific cho từng workflow
   - Extend từ BaseTask
   - Lưu thông tin xử lý

## 4. API Endpoints

### 4.1 Job Management
```
POST /api/jobs
- Create new job
- Parameters: workflow_name, file_path, channel_name, priority

GET /api/jobs/{job_id}
- Get job status
- Returns: job details and status
```

### 4.2 Workflow Specific
```
POST /api/{workflow_name}/process
- Process specific workflow
- Parameters: based on workflow

GET /api/{workflow_name}/status/{task_id}
- Get workflow task status
```

## 5. Thêm Workflow Mới

1. **Tạo Cấu Trúc**
   ```
   /workflows/new_workflow/
       __init__.py
       config.py
       /models/
       /services/
       /utils/
   ```

2. **Implement Components**
   - Tạo processor class kế thừa BaseProcessor
   - Tạo models kế thừa BaseTask
   - Tạo watcher kế thừa BaseWatcher

3. **Cấu Hình**
   - Thêm config vào settings
   - Setup database models
   - Cấu hình đường dẫn

4. **Đăng Ký**
   ```python
   job_manager.register_workflow(
       name="new_workflow",
       processor=NewWorkflowProcessor(config)
   )
   ```

## 6. Monitoring và Maintenance

### 6.1 Logging
- Structured logging cho mọi operation
- Separate logs cho từng workflow
- Error tracking và alerting

### 6.2 Monitoring
- Job queue status
- Processing times
- Error rates
- Resource usage

### 6.3 Maintenance
- Regular cleanup của archived files
- Database optimization
- Log rotation
- Backup procedures

## 7. Security

### 7.1 File Security
- Input validation
- File type checking
- Size limits
- Virus scanning

### 7.2 API Security
- Authentication
- Rate limiting
- Input sanitization
- Error handling

## 8. Performance Optimization

### 8.1 Job Queue
- Priority based processing
- Efficient queue management
- Resource allocation

### 8.2 File Processing
- Chunk processing
- Memory management
- Parallel processing (khi cần)

## 9. Troubleshooting

### Common Issues
1. Job stuck in processing
2. File watcher không hoạt động
3. Database connection issues
4. Processing errors

### Solutions
- Check logs
- Verify file permissions
- Monitor resource usage
- Validate configurations
