from flask import Flask, request, render_template_string, send_file
import requests
import subprocess
import os
import threading
import time
import shutil

# Flask-Setup
app = Flask(__name__)

# API-Schlüssel aus token.txt laden
with open("token.txt", "r") as f:
    YOUTUBE_API_KEY = f.read().strip()

# Konstanten
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
RIITUBE_BASE_URL = "https://riitube.rc24.xyz/"
VIDEO_FOLDER = "videos"

# Videos-Ordner erstellen, falls nicht vorhanden
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# Maximum size limits (1 GB and 5 GB)
MAX_VIDEO_SIZE = 1 * 1024 * 1024 * 1024  # 1 GB
MAX_FOLDER_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB

# Helper function to calculate the total size of the folder
def get_folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            file_path = os.path.join(dirpath, f)
            total_size += os.path.getsize(file_path)
    return total_size

# Function to periodically delete videos every 5 minutes
def delete_videos_periodically():
    while True:
        time.sleep(86400)  # 5 minutes
        for filename in os.listdir(VIDEO_FOLDER):
            file_path = os.path.join(VIDEO_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted: {file_path}")

# Start the periodic deletion in a separate thread
threading.Thread(target=delete_videos_periodically, daemon=True).start()

# HTML-Templates als Strings
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReviveTube by ReviveMii</title>
</head>
<body style="text-align: center; font-family: Arial, sans-serif;">
    <h1>ReviveTube by ReviveMii</h1>
    <form action="/" method="get">
        <input type="text" name="query" placeholder="Search YouTube" style="width: 300px; padding: 10px; font-size: 16px;">
        <button type="submit" style="padding: 10px 20px; font-size: 16px;">Go</button>
    </form>
    {% if results %}
        <h2>Search Results</h2>
        <ul style="list-style: none; padding: 0;">
            {% for video in results %}
                <li style="margin-bottom: 20px;">
                    <a href="/watch?video_id={{ video['id'] }}" style="text-decoration: none; color: #000;">
                        <img src="{{ video['thumbnail'] }}" alt="{{ video['title'] }}" style="width: 320px; height: 180px;"><br>
                        <strong>{{ video['title'] }}</strong><br>
                        <small>By: {{ video['uploader'] }}</small>
                    </a>
                </li>
            {% endfor %}
        </ul>
    {% endif %}
    <br>
    <a href="http://old.errexe.xyz" target="_blank" style="font-size: 14px; color: blue; text-decoration: underline;">Visit ReviveMii</a>
    <p style="font-size: 12px;">This app uses the RiiConnect24 WiiMC API. We are NOT afiliated with RiiConnect24, Nintendo or YouTube. This app is using Code from Wiinet.xyz.</p>
    <p style="color: blue">It's recommend to bookmark this Page</p>
    <p>It's normal that Sites take long to load</p>
</body>
</html>
"""

WATCH_WII_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReviveTube Video</title>
</head>
<body style="text-align: center; font-family: Arial, sans-serif;">
    <div style="width: 100%; background-color: #000; text-align: center;">
        <object type="application/x-shockwave-flash" data="player.swf" width="384" height="256">
            <param name="wmode" value="transparent">
            <param name="allowFullScreen" value="false">
            <param name="flashvars" value="filename={{ video_flv }}">
        </object>
    </div>
    <p>If the video does not play smoothly, restart the Internet Channel by pressing the Home button and then Reset. It's a bug. It happens if you visit too many Sites</p>
</body>
</html>
"""

WATCH_STANDARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReviveTube Video</title>
</head>
<body style="text-align: center; font-family: Arial, sans-serif;">
    <h1>ReviveTube Video</h1>
    <video width="640" height="360" controls>
        <source src="{{ video_mp4 }}" type="video/mp4">
        Your browser does not support the video tag.
    </video>
</body>
</html>
"""

# Routen
@app.route("/", methods=["GET"])
def index():
    query = request.args.get("query")
    results = None

    if query:
        # YouTube API aufrufen
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 10,
            "key": YOUTUBE_API_KEY,
        }
        response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=3)
        data = response.json()

        # Ergebnisse verarbeiten
        if response.status_code == 200 and "items" in data:
            results = [
                {
                    "id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "uploader": item["snippet"]["channelTitle"],
                    "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                }
                for item in data.get("items", [])
            ]
    return render_template_string(INDEX_TEMPLATE, results=results)


@app.route("/watch", methods=["GET"])
def watch():
    video_id = request.args.get("video_id")
    if not video_id:
        return "Missing video ID.", 400

    # User-Agent prüfen
    user_agent = request.headers.get("User-Agent", "").lower()
    is_wii = "wii" in user_agent and "wiiu" not in user_agent

    # Video-Pfade
    video_mp4_path = os.path.join(VIDEO_FOLDER, f"{video_id}.mp4")
    video_flv_path = os.path.join(VIDEO_FOLDER, f"{video_id}.flv")

    # Video herunterladen, falls nicht vorhanden
    if not os.path.exists(video_mp4_path):
        video_url = f"{RIITUBE_BASE_URL}video/wii/?q={video_id}"

        try:
            response = requests.get(video_url, stream=True, timeout=10)
            if response.status_code != 200:
                return f"Failed to download video. HTTP Status: {response.status_code}, Reason: {response.reason}", 500
            
            # Check file size during download
            total_size = 0
            with open(video_mp4_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total_size += len(chunk)
                    if total_size > MAX_VIDEO_SIZE:
                        os.remove(video_mp4_path)
                        return "Video exceeds 1 GB in size.", 400

        except requests.exceptions.RequestException as e:
            return f"An error occurred while downloading the video: {str(e)}", 500

    # Check folder size
    if get_folder_size(VIDEO_FOLDER) > MAX_FOLDER_SIZE:
        shutil.rmtree(VIDEO_FOLDER)
        os.makedirs(VIDEO_FOLDER, exist_ok=True)  # Recreate the folder after deletion
        return "The video folder exceeded 5 GB and was deleted.", 400

    # Für Wii in FLV umwandeln
    if is_wii and not os.path.exists(video_flv_path):
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", video_mp4_path,
                    "-ar", "22050",
                    "-f", "flv",
                    "-s", "320x240",
                    "-ab", "32k",
                    "-filter:v", "fps=fps=15",
                    video_flv_path
                ],
                check=True
            )
        except subprocess.CalledProcessError as e:
            return f"Failed to convert video. Try reloading the Page. Error: {str(e)}", 500

    # Passendes Template rendern
    if is_wii:
        return render_template_string(WATCH_WII_TEMPLATE, video_flv=f"/videos/{video_id}.flv")
    else:
        return render_template_string(WATCH_STANDARD_TEMPLATE, video_mp4=f"/videos/{video_id}.mp4")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_file(os.path.join(filename))


if __name__ == "__main__":
    app.run(debug=True)
