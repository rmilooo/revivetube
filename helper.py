import json
import os
import subprocess


def read_file(path):
    assert isinstance(path, str), "Path must be a string"

    try:
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return "Error: File not found."
    except Exception as e:
        return f"Error: {str(e)}"


def get_video_duration_from_file(video_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        video_info = json.loads(result.stdout)

        duration = float(video_info['format']['duration'])

        return duration
    except Exception as e:
        print(f"Can't fetch Video-Duration: {str(e)}")
        return 0

def format_duration(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{str(seconds).zfill(2)}"


def get_file_size(file_path):
    return os.path.getsize(file_path)


def get_range(file_path, byte_range):
    with open(file_path, 'rb') as f:
        f.seek(byte_range[0])
        return f.read(byte_range[1] - byte_range[0] + 1)


def get_api_key():
    try:
        with open("token.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError("Missing token.txt. Please go to README.md")