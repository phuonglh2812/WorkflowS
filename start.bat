@echo off
REM Script để tự động activate môi trường Conda và chạy main.py

REM Kích hoạt Conda
CALL conda activate "C:\Users\phuon\.conda\envs\xtts_api_server_installer"

REM Chạy script Python
python main.py

REM Giữ cửa sổ terminal mở sau khi hoàn thành
echo.
echo === Script đã chạy xong, nhấn phím bất kỳ để thoát ===
pause >nul
