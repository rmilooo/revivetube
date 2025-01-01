import json
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