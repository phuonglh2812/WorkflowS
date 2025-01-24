import os
import sys
from PIL import Image, ImageDraw, ImageFont
from tkinter import filedialog, Tk
import argparse
import re
import logging

# Đặt encoding cho stdout để hỗ trợ tiếng Việt
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Tạo logger
logger = logging.getLogger(__name__)

# Hàm đọc nội dung từ file text
def read_text_from_file(text_file: str) -> str:
    """Đọc nội dung từ file văn bản"""
    encodings = ['utf-8', 'ISO-8859-1', 'windows-1252', 'utf-16']
    for enc in encodings:
        try:
            with open(text_file, 'r', encoding=enc) as file:
                return file.read()
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode {text_file} with encoding {enc}. Trying next...")
    raise Exception(f"Could not read the file {text_file} with any known encoding.")

# Hàm tách văn bản thành các dòng
def wrap_text_to_lines(text, font, max_width):
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        if font.getlength(test_line) > max_width:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines

# Hàm vẽ văn bản vào ảnh nền
def add_text_to_thumbnail(base_image_path, text, output_path, font_path):
    try:
        base_img = Image.open(base_image_path).convert("RGBA")
        base_img = base_img.resize((1920, 1080))

        draw = ImageDraw.Draw(base_img)
        rectangle_x1, rectangle_y1 = 60, 360
        rectangle_x2, rectangle_y2 = 1860, 960
        draw.rectangle([rectangle_x1, rectangle_y1, rectangle_x2, rectangle_y2], fill="white")

        rectangle_width = rectangle_x2 - rectangle_x1
        rectangle_height = rectangle_y2 - rectangle_y1
        max_lines = 4

        font_size = 150
        font = ImageFont.truetype(font_path, font_size)

        while font_size > 5:
            lines = wrap_text_to_lines(text, font, rectangle_width)
            if len(lines) <= max_lines:
                total_text_height = font.getbbox("Test")[3] * len(lines)
                if total_text_height <= rectangle_height:
                    break
            font_size -= 2
            font = ImageFont.truetype(font_path, font_size)

        line_height = font.getbbox("Test")[3]
        total_text_height = line_height * len(lines)
        spacing = (rectangle_height - total_text_height) // (len(lines) - 1) if len(lines) > 1 else 0

        y_position = rectangle_y1
        for line in lines:
            draw.text((rectangle_x1, y_position), line, font=font, fill="black")
            y_position += line_height + spacing

        base_img.save(output_path, format="PNG")
        print(f"Created thumbnail: {output_path}")

    except Exception as e:
        print(f"Error processing image: {e}")

# Hàm tạo ảnh nền trong suốt chứa thumbnail gốc
def create_transparent_overlay(thumbnail_path, output_path):
    try:
        thumbnail_img = Image.open(thumbnail_path).convert("RGBA")
        thumbnail_resized = thumbnail_img.resize((1200, 675))

        transparent_img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        center_x = (1920 - 1200) // 2
        center_y = (1080 - 675) // 2

        transparent_img.paste(thumbnail_resized, (center_x, center_y), thumbnail_resized)

        transparent_img.save(output_path, format="PNG")
        print(f"Created transparent overlay: {output_path}")

    except Exception as e:
        print(f"Error creating transparent overlay: {e}")

# Hàm làm sạch tên file
def clean_filename(filename):
    return re.sub(r'[<>:\"/\\|?*]', '_', filename)

# Hàm xử lý một file văn bản
def generate_single_thumbnail(base_image_path, text_file, output_dir, font_path):
    try:
        # Kiểm tra file input tồn tại
        for file_path in [base_image_path, text_file, font_path]:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Input file not found: {file_path}")
        
        # Kiểm tra và tạo thư mục output
        os.makedirs(output_dir, exist_ok=True)
        if not os.access(output_dir, os.W_OK):
            raise PermissionError(f"No write permission for output directory: {output_dir}")

        # Đọc text từ file
        logger.info(f"Reading text from file: {text_file}")
        text = read_text_from_file(text_file)
        if not text.strip():
            raise ValueError(f"Text file is empty: {text_file}")

        # Tạo tên file output
        text_name = os.path.splitext(os.path.basename(text_file))[0]
        thumbnail_path = os.path.join(output_dir, f"{text_name}_thumbnail.png")
        transparent_path = os.path.join(output_dir, f"{text_name}.png")

        # Tạo thumbnail
        logger.info(f"Creating thumbnail with text: {text[:50]}...")
        add_text_to_thumbnail(base_image_path, text, thumbnail_path, font_path)
        
        # Kiểm tra file thumbnail đã được tạo
        if not os.path.exists(thumbnail_path):
            raise FileNotFoundError(f"Failed to create thumbnail: {thumbnail_path}")

        # Tạo transparent overlay
        logger.info("Creating transparent overlay...")
        create_transparent_overlay(thumbnail_path, transparent_path)
        
        # Kiểm tra file transparent đã được tạo
        if not os.path.exists(transparent_path):
            raise FileNotFoundError(f"Failed to create transparent overlay: {transparent_path}")

        logger.info("Successfully created both thumbnail and transparent overlay")
        return thumbnail_path, transparent_path

    except Exception as e:
        logger.error(f"Error in generate_single_thumbnail: {str(e)}")
        raise

# Hàm xử lý chính
def generate_thumbnails(base_image_path, input_texts_dir, output_dir, font_path):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    text_files = [f for f in os.listdir(input_texts_dir) if f.lower().endswith('.txt')]

    if not text_files:
        print("No text files found in the directory.")
        return

    for text_file in text_files:
        text_path = os.path.join(input_texts_dir, text_file)
        text = read_text_from_file(text_path)

        safe_text_name = clean_filename(os.path.splitext(os.path.basename(text_file))[0])
        original_output_path = os.path.join(output_dir, f"{safe_text_name}_thumbnail.png")
        transparent_output_path = os.path.join(output_dir, f"{safe_text_name}.png")

        add_text_to_thumbnail(base_image_path, text, original_output_path, font_path)
        create_transparent_overlay(original_output_path, transparent_output_path)

# GUI chọn thư mục
def gui_mode():
    root = Tk()
    root.withdraw()

    print("Select background image (1920x1080):")
    base_image_path = filedialog.askopenfilename(title="Select background image", filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])

    print("Do you want to process a single file or all files?")
    mode = input("Enter '1' to process a single file, '2' to process all files: ").strip()

    if mode == "1":
        print("Select text file to process:")
        text_file = filedialog.askopenfilename(title="Select text file", filetypes=[("Text files", "*.txt")])

        print("Select output directory:")
        output_dir = filedialog.askdirectory(title="Select output directory")

        print("Select font:")
        font_path = filedialog.askopenfilename(title="Select font", filetypes=[("Font files", "*.ttf;*.otf")])

        if base_image_path and text_file and output_dir and font_path:
            generate_single_thumbnail(base_image_path, text_file, output_dir, font_path)
        else:
            print("Please select all required information!")

    elif mode == "2":
        print("Select directory containing text files:")
        input_texts_dir = filedialog.askdirectory(title="Select directory containing text files")

        print("Select output directory:")
        output_dir = filedialog.askdirectory(title="Select output directory")

        print("Select font:")
        font_path = filedialog.askopenfilename(title="Select font", filetypes=[("Font files", "*.ttf;*.otf")])

        if base_image_path and input_texts_dir and output_dir and font_path:
            generate_thumbnails(base_image_path, input_texts_dir, output_dir, font_path)
        else:
            print("Please select all required information!")
    else:
        print("Invalid choice. Please run again!")

# Chạy từ dòng lệnh hoặc GUI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create thumbnail from text and background image.")
    parser.add_argument("--base_image", help="Path to background image (1920x1080).")
    parser.add_argument("--text_file", help="Path to single text file.")
    parser.add_argument("--texts_dir", help="Directory containing text files.")
    parser.add_argument("--output_dir", help="Directory to save thumbnails.")
    parser.add_argument("--font_path", help="Path to font file.")
    args = parser.parse_args()

    if args.base_image and args.text_file and args.output_dir and args.font_path:
        generate_single_thumbnail(args.base_image, args.text_file, args.output_dir, args.font_path)
    elif args.base_image and args.texts_dir and args.output_dir and args.font_path:
        generate_thumbnails(args.base_image, args.texts_dir, args.output_dir, args.font_path)
    else:
        print("Not enough command line arguments. Switching to GUI mode...")
        gui_mode()
