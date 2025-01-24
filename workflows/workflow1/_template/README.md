# Template Channel

Đây là template channel với cấu trúc thư mục và config mẫu.
Copy toàn bộ thư mục này và đổi tên thành tên channel mới để bắt đầu.

## Cấu trúc thư mục:
- Scripts/: Chứa các file script cần xử lý
- Working/: Chứa các file đang được xử lý
- Completed/: Chứa các file đã xử lý xong
- Error/: Chứa các file xử lý lỗi
- Final/: Chứa các video đầu ra
- Assets/
  - Overlay1/: Chứa logo cố định (logo.png)
  - Overlay2/: Chứa các overlay ngẫu nhiên
- config.json: Cấu hình cho voice service
- preset.json: Cấu hình cho video service

## Config files:
1. config.json - Voice settings:
```json
{
    "voice_settings": {
        "speaker_voice": "EN_Ivy_Female",
        "language": "en",
        "speed": 1,
        "temperature": 0.75,
        "length_penalty": 1,
        "repetition_penalty": 5,
        "top_k": 50,
        "top_p": 0.85,
        "stream_chunk_size": 200,
        "enable_text_splitting": true,
        "max_sentence_length": 100,
        "enable_sentence_splitting": true
    }
}
```

2. preset.json - Video settings:
```json
{
    "video_settings": {
        "preset_name": "1"
    }
}
```

## Quy trình làm việc:
1. Copy template channel này thành channel mới
2. Chỉnh sửa config.json và preset.json theo nhu cầu
3. Thêm logo vào Overlay1/logo.png
4. Thêm các overlay vào Overlay2/
5. Đặt file script vào Scripts/ để bắt đầu xử lý
