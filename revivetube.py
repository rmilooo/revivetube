"""
(c) 2024 ReviveMii Project. All rights reserved. If you want to use this Code, give Credits to ReviveMii Project. https://revivemii.fr.to/

ReviveMii Project and TheErrorExe is the Developer of this Code. Modification, Network Use and Distribution is allowed if you leave this Comment in the beginning of the Code, and if a website exist, Credits on the Website.

This Code uses the Invidious API, Google API and yt-dlp. This Code is designed to run on Ubuntu 24.04.

Don’t claim that this code is your code. Don't use it without Credits to the ReviveMii Project. Don't use it without this Comment. Don't modify this Comment.

ReviveMii's Server Code is provided "as-is" and "as available." We do not guarantee uninterrupted access, error-free performance, or compatibility with all Wii systems. ReviveMii project is not liable for any damage, loss of data, or other issues arising from the use of this service and code.

If you use this Code, you agree to https://revivemii.fr.to/revivetube/t-and-p.html, also available as http only Version: http://old.errexe.xyz/revivetube/t-and-p.html

ReviveMii Project: https://revivemii.fr.to/
"""

import json
import isodate
from flask import Flask, request, render_template_string, send_file, Response, abort, jsonify
import tempfile
import shutil
import yt_dlp
import requests
import subprocess
import os
import threading
from threading import Thread
import time

app = Flask(__name__)

def check_and_create_folder():
    while True:
        folder_path = './sigma/videos'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Ordner {folder_path} wurde erstellt.")
        time.sleep(10)

def start_folder_check():
    thread = Thread(target=check_and_create_folder)
    thread.daemon = True
    thread.start()


VIDEO_FOLDER = "sigma/videos"
API_BASE_URL = "https://y.com.sb/api/v1/"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
video_status = {}

LOADING_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Loading...</title>
    <style>
        body {
            text-align: center;
            font-family: Arial, sans-serif;
        }
        #loadingGif {
            width: 50px;
            height: 50px;
            margin: 20px auto;
        }
        #goButton {
            display: none;
            margin-top: 20px;
            padding: 10px 20px;
            font-size: 16px;
            background-color: #4caf50;
            color: white;
            border: none;
            cursor: pointer;
        }
       #goButton:disabled {
            background-color: gray;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <h1>Loading</h1>
    <img id="loadingGif" src="loading.gif" alt="Loading..." />
    <p id="progressText">Fetching Info...</p>
    <button id="goButton" onclick="startVideo()">Go</button>
    <br>
    <small style="color: grey">Loading Screen will NOT work in Dolphin Emulator.<br><br>Long Video = Longer Download and Converting.<br><br>For videos longer than 7 minutes, there is a chance that they won’t play.</small>
    <script type="text/javascript">
    var goButton = document.getElementById('goButton');
    var loadingGif = document.getElementById('loadingGif');
    var progressText = document.getElementById('progressText');
    var videoId = "{{ video_id }}"; // Pass video_id from Flask to the template

    function simulateLoading() {
        setInterval(checkStatus, 1000);
    }

    function checkStatus() {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/status/' + videoId, true);
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr.status === 200) {
                var response;
                try {
                    response = eval('(' + xhr.responseText + ')');
                } catch (e) {
                    response = { status: 'error' };
                }
                updateProgress(response);
            }
        };
        xhr.send();
    }

    function updateProgress(status) {
        if (status.status === 'complete') {
            loadingGif.style.display = 'none';
            progressText.innerHTML = 'Done!';
            goButton.style.display = 'inline'; // "inline-block" wird nicht überall unterstützt
        } else if (status.status === 'downloading') {
            progressText.innerHTML = 'The Server is Downloading...';
        } else if (status.status === 'converting') {
            progressText.innerHTML = 'The Server is Converting video...';
        } else if (status.status === 'converting for Wii') {
            progressText.innerHTML = 'The Server is Converting for Wii...';
        } else {
            progressText.innerHTML = 'The Server was unable to process the video! Report the Bug in the Discord Server. <br> Error Details for Developers: {{ video_id }}_unable_1.<br>Discord Server on ReviveMii Homepage Footer';
        }
    }

    function startVideo() {
        window.location.href = '/watch?video_id=' + videoId;
    }

    window.onload = function () {
        simulateLoading();
    };
</script>
</body>
</html>"""
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
        raise FileNotFoundError("Die Datei token.txt wurde nicht gefunden. Bitte stelle sicher, dass sie vorhanden ist.")

os.makedirs(VIDEO_FOLDER, exist_ok=True)

MAX_VIDEO_SIZE = 1 * 1024 * 1024 * 1024  
MAX_FOLDER_SIZE = 5 * 1024 * 1024 * 1024  

def get_folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            file_path = os.path.join(dirpath, f)
            total_size += os.path.getsize(file_path)
    return total_size

def delete_videos_periodically():
    while True:
        time.sleep(86400)  
        for filename in os.listdir(VIDEO_FOLDER):
            file_path = os.path.join(VIDEO_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted: {file_path}")

threading.Thread(target=delete_videos_periodically, daemon=True).start()

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ReviveTube by ReviveMii</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            color: #fff;
            background-color: #181818;
            text-align: center; /* Zentriert den Text */
        }
        h1 {
            color: #ff0000;
            font-size: 28px;
            margin-bottom: 20px;
        }
        p, h2 {
            font-size: 16px;
            margin-bottom: 10px;
        }
        .search-bar {
            width: 300px;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ccc;
            border-radius: 4px;
            display: block; /* Block-Level für zentrierten Abstand */
            margin: 0 auto; /* Zentriert das Eingabefeld */
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            background-color: #333333;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 4px;
            display: block;
            margin: 10px auto; /* Zentriert den Button */
        }
        .video-item {
            margin-bottom: 20px;
            text-align: center; /* Zentriert jedes Video-Item */
        }
        .video-item img {
            width: 320px;
            height: 180px;
            border-radius: 8px;
        }
        .video-item-title {
            color: #fff;
            font-weight: bold;
            font-size: 16px;
            text-align: center;
        }
        .video-item-uploader {
            color: #ccc;
            font-size: 14px;
            text-align: center;
        }
        .video-item-duration {
            color: #ccc;
            font-size: 14px;
            text-align: center;
            margin-top: 5px;
        }
        .dark-mode {
            background-color: #181818;
            color: #fff;
        }
        .dark-mode a {
            color: #1e90ff;
        }
    </style>
</head>
<body class="dark-mode" id="page-body">
    <h1>ReviveTube by ReviveMii</h1>
    <p>A YouTube App for the Wii</p>
    <form action="/" method="get">
        <input class="search-bar" type="text" name="query" placeholder="Search YouTube">
        <button type="submit">Go</button>
    </form>
    {% if results %}
        <h2>Search Results</h2>
        <div>
            {% for video in results %}
                <div class="video-item">
                    <a href="/watch?video_id={{ video['id'] }}">
                        <img src="{{ video['thumbnail'] }}" alt="{{ video['title'] }}">
                        <div class="video-item-title">{{ video['title'] }}</div>
                        <div class="video-item-uploader">By: {{ video['uploader'] }}</div>
                        <div class="video-item-duration">Duration: {{ video['duration'] }}</div>
                    </a>
                </div>
            {% endfor %}
        </div>
    {% endif %}
    <p><a href="http://revivemii.errexe.xyz" target="_blank">Visit ReviveMii</a></p>
    <p><a href="http://old.errexe.xyz" target="_blank">Visit ReviveMii (HTTP Only Version for the Wii)</a></p>
    <p style="color: red;">\/ Scroll down \/</p>
    <p style="font-size: 12px;">We are NOT affiliated with Nintendo or YouTube. This app uses code from Wiinet.xyz. For more information, scroll down to Open Source Software.</p>
    <p style="color: blue">It's recommended to bookmark this page. Some sites may take longer to load.</p>
    <a href="http://old.errexe.xyz/revivetube/t-and-p.html">Terms of Service and Privacy Policy (Last Updated: 7. Dec 2024 12:41 CET)</a><br><br>
    <a href="https://github.com/ReviveMii/revivetube/" target="_blank">Source Code</a><br><br>
    <a href="http://old.errexe.xyz/discord-redirect.html">Discord Server [Use a Compatible Device]</a>
    <p>Version: v2 Beta (Sometimes I forget to update the Version Number)</p>
    <a href="/licenses.html">Open Source Software Used in This App</a>
    <br>
    <a href="mailto:theerrorexe@gmail.com">Contact</a>
    <br>
    <a href="/bf.html">Report Bugs & Feedback</a>
</body>
</html>
"""

WATCH_STANDARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body { font-family: 'Arial', sans-serif; text-align: center; color: #fff; background-color: #181818; }
        video { margin-top: 20px; }
        h1 { color: #ff0000; font-size: 24px; }
        h3, p { font-size: 16px; }
        .comments { text-align: left; margin: 0 auto; width: 80%; font-size: 14px; }
        .comment { margin-bottom: 15px; padding: 10px; border-bottom: 1px solid #ddd; }
        .comment p { font-size: 14px; }
        .dark-mode { background-color: #181818; color: #fff; }
        .dark-mode a { color: #1e90ff; }
    </style>
</head>
<!-- <body class="dark-mode" id="page-body">
   <video width="640" height="360" controls>
 <source src="{{ video_mp4 }}" type="video/mp4">
 Your browser does not support the video tag.
    </video>
    <h1>{{ title }}</h1>
    <h3>Uploaded by: <a href="/channel?channel_id={{ channelId }}">{{ uploader }}</a></h3>
    <p><strong>Views:</strong> {{ viewCount }}</p>
    <p><strong>Likes:</strong> {{ likeCount }}</p>
    <p><strong>Upload Date:</strong> {{ publishedAt }}</p>
    <a href="#comments">Skip Description</a>
    
    <h3>Description:</h3>
    <p>{{ description | safe }}</p>
    <h3 id="comments" class="comments">Comments:</h3>
    <div class="comments">
        {% if comments %}
            {% for comment in comments %}
                <div class="comment">
                    <p><strong>{{ comment.author }}</strong> posted:</p>
                    <p>{{ comment.text|safe }}</p>
                    <p style="color: gray; font-size: 12px;">Likes: {{ comment.likeCount }} | Post date: {{ comment.publishedAt }}</p>
                </div>
            {% endfor %}
        {% else %}
            <p>No Comments.</p>
        {% endif %}
    </div> -->
Please access this Site on a Wii
</body>
</html>
"""

WATCH_WII_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
<style>
    body {
        font-family: 'Arial', sans-serif;
        text-align: center; /* Zentriert den Text */
        color: #fff;
        background-color: #181818;
    }
    .dark-mode {
        background-color: #181818;
        color: #fff;
    }
    .dark-mode a {
        color: #1e90ff;
    }
    .comments {
        margin: 0 auto;
        width: 80%;
    }
    h1 {
        color: red;
        text-align: center; /* Zentriert den Titel */
    }
    h3 {
        color: white;
        text-align: center;
    }
</style>
</head>
<body class="dark-mode" id="page-body">
 <div style="width: 100%; background-color: #000; text-align: center;">
        <object type="application/x-shockwave-flash" data="/player.swf" width="384" height="256">
            <param name="wmode" value="transparent">
            <param name="allowFullScreen" value="false">
            <param name="flashvars" value="filename={{ video_flv }}">
        </object>
    </div>
    <h1 style="color: red">{{ title }}</h1>
    <h3>Uploaded by: <a href="/channel?channel_id={{ channelId }}">{{ uploader }}</a></h3>
    <p><strong>Views:</strong> {{ viewCount }}</p>
    <p><strong>Likes:</strong> {{ likeCount }}</p>
    <p><strong>Upload Date:</strong> {{ publishedAt }}</p>
    <a href="#comments">Skip Description</a>
    <h3 style="color: red">Description:</h3>
    <p>{{ description | safe }}</p>
    <h3 id="comments" class="comments" style="color: red">Comments:</h3>
    <div class="comments">
        {% if comments %}
            {% for comment in comments %}
                <div class="comment">
                    <p><strong>{{ comment.author }}</strong> posted:</p>
                    <p>{{ comment.text|safe }}</p>
                    <p style="color: gray; font-size: 12px;">Likes: {{ comment.likeCount }} | Post date: {{ comment.publishedAt }}</p>
                </div>
            {% endfor %}
        {% else %}
            <p>No Comments.</p>
        {% endif %}
    </div>
</body>
</html>
"""
@app.route("/thumbnail/<video_id>")
def get_thumbnail(video_id):
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    try:

        response = requests.get(thumbnail_url, stream=True, timeout=1)
        if response.status_code == 200:

            return send_file(
                response.raw,
                mimetype=response.headers.get("Content-Type", "image/jpeg"),
                as_attachment=False,
            )
        else:
            return f"Failed to fetch thumbnail. Status: {response.status_code}", 500
    except requests.exceptions.RequestException as e:
        return f"Error fetching thumbnail: {str(e)}", 500

def get_video_comments(video_id, max_results=20):
    """
    Ruft die letzten Kommentare für ein YouTube-Video ab.
    """
    api_key = get_api_key()

    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": max_results,
        "order": "relevance"  
    }

    try:
        response = requests.get("https://www.googleapis.com/youtube/v3/commentThreads", params=params, timeout=3)
        response.raise_for_status()

        data = response.json()

        comments = []
        if "items" in data:
            for item in data["items"]:
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": snippet["authorDisplayName"],
                    "text": snippet["textDisplay"],
                    "likeCount": snippet.get("likeCount", 0),
                    "publishedAt": snippet["publishedAt"]
                })

        return comments

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Kommentare: {str(e)}")
        return []
@app.route("/switch_wii", methods=["GET"])
def switch_wii():
    video_id = request.args.get("video_id")
    if not video_id:
        return "Fehlende Video-ID.", 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Nintendo Wii; U; ; en) Opera/9.30 (Nintendo Wii)"
    }

    response = requests.get(f"http://localhost:5000/watch?video_id={video_id}", headers=headers, timeout=2)

    if response.status_code == 200:
        return response.text
    else:
        return "Fehler beim Abrufen des Videos im Wii-Modus.", 500

@app.route("/switch_n", methods=["GET"])
def switch_n():
    video_id = request.args.get("video_id")
    if not video_id:
        return "Fehlende Video-ID.", 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    response = requests.get(f"http://localhost:5000/watch?video_id={video_id}", headers=headers, timeout=2)

    if response.status_code == 200:
        return response.text
    else:
        return "Fehler beim Abrufen des Videos im normalen Modus.", 500

@app.route("/", methods=["GET"])
def index():
    query = request.args.get("query")
    results = None

    if query:
        response = requests.get(f"https://y.com.sb/api/v1/search?q={query}", timeout=3)
        try:
            data = response.json()
        except ValueError:
            return "Fehler beim Parsen der API-Antwort.", 500

        if response.status_code == 200 and isinstance(data, list):
            results = [
                {
                    "id": entry.get("videoId"),
                    "title": entry.get("title"),
                    "uploader": entry.get("author", "Unbekannt"),
                    "thumbnail": f"/thumbnail/{entry['videoId']}",
                    "viewCount": entry.get("viewCountText", "Unbekannt"),
                    "published": entry.get("publishedText", "Unbekannt"),
                    "duration": format_duration(entry.get("lengthSeconds", 0))  # Video Dauer formatiert
                }
                for entry in data
                if entry.get("videoId")
            ]
        else:
            return "Keine Ergebnisse gefunden oder Fehler in der API-Antwort.", 404

    return render_template_string(INDEX_TEMPLATE, results=results)

def format_duration(seconds):
    """Formatiert die Dauer von Sekunden in Minuten:Sekunden."""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{str(seconds).zfill(2)}"

def get_video_duration_from_file(video_path):
    """
    Holt die Dauer eines Videos aus der Datei (FLV oder MP4) mithilfe von ffprobe.
    Gibt die Dauer in Sekunden zurück.
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        video_info = json.loads(result.stdout)
        
        duration = float(video_info['format']['duration'])
        
        return duration
    except Exception as e:
        print(f"Fehler beim Abrufen der Video-Dauer: {str(e)}")
        return 0


@app.route("/fullscreen", methods=["GET"])
def fullscreen():
    video_id = request.args.get("video_id")
    if not video_id:
        return "Fehlende Video-ID.", 400

    return render_template_string(FULLSCREEN, video_id=video_id)

@app.route("/watch", methods=["GET"])
def watch():
    video_id = request.args.get("video_id")
    if not video_id:
        return "Fehlende Video-ID.", 400

    video_mp4_path = os.path.join(VIDEO_FOLDER, f"{video_id}.mp4")
    video_flv_path = os.path.join(VIDEO_FOLDER, f"{video_id}.flv")

    if video_id not in video_status:
        video_status[video_id] = {"status": "processing"}

    user_agent = request.headers.get("User-Agent", "").lower()
    is_wii = "wii" in user_agent and "wiiu" not in user_agent

    try:
        response = requests.get(f"http://localhost:5000/video_metadata/{video_id}", timeout=20)
        if response.status_code == 200:
            metadata = response.json()
        else:
            return f"Fehler beim Abrufen der Metadaten für Video-ID {video_id}.", 500
    except requests.exceptions.RequestException as e:
        return f"Fehler bei der Verbindung zur Metadaten-API: {str(e)}", 500


    comments = []
    try:
        comments = get_video_comments(video_id)
    except Exception as e:
        print(f"Fehler beim Abrufen der Kommentare: {str(e)}")
        comments = []

    if os.path.exists(video_mp4_path):
        video_duration = get_video_duration_from_file(video_flv_path)
        alert_script = ""
        if video_duration > 420:
            alert_script = """
            <script type="text/javascript">
                alert("This Video is long. There is a chance that the Wii will not play the Video. Try a Video under 7 minutes or something like that.");
            </script>
            """
        
        if is_wii and os.path.exists(video_flv_path):
            return render_template_string(WATCH_WII_TEMPLATE + alert_script, 
                                          title=metadata['title'], 
                                          uploader=metadata['uploader'], 
                                          channelId=metadata['channelId'],
                                          description=metadata['description'].replace("\n", "<br>"),
                                          viewCount=metadata['viewCount'], 
                                          likeCount=metadata['likeCount'],
                                          publishedAt=metadata['publishedAt'],
                                          comments=comments,
                                          video_id=video_id, 
                                          video_flv=f"/sigma/videos/{video_id}.flv",
                                          alert_message="")

        return render_template_string(WATCH_STANDARD_TEMPLATE, 
                                      title=metadata['title'], 
                                      uploader=metadata['uploader'], 
                                      channelId=metadata['channelId'],
                                      description=metadata['description'].replace("\n", "<br>"),
                                      viewCount=metadata['viewCount'], 
                                      likeCount=metadata['likeCount'], 
                                      publishedAt=metadata['publishedAt'],
                                      comments=comments,
                                      video_id=video_id,
                                      video_mp4=f"/sigma/videos/{video_id}.mp4",
                                      alert_message="")

    if not os.path.exists(video_mp4_path):
        if video_status[video_id]["status"] == "processing":
            threading.Thread(target=process_video, args=(video_id,)).start()
        return render_template_string(LOADING_TEMPLATE, video_id=video_id)

def process_video(video_id):
    video_mp4_path = os.path.join(VIDEO_FOLDER, f"{video_id}.mp4")
    video_flv_path = os.path.join(VIDEO_FOLDER, f"{video_id}.flv")
    try:

        video_status[video_id] = {"status": "downloading"}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_video_path = os.path.join(temp_dir, f"{video_id}.%(ext)s")
            command = [
                "yt-dlp",
                "-f worstvideo+worstaudio",
                "--force-ipv4",
                "-o", temp_video_path,
                f"https://m.youtube.com/watch?v={video_id}"
            ]
            subprocess.run(command, check=True)

            downloaded_files = [f for f in os.listdir(temp_dir) if video_id in f]
            if not downloaded_files:
                video_status[video_id] = {"status": "error", "message": "Download fehlgeschlagen."}
                return

            downloaded_file = os.path.join(temp_dir, downloaded_files[0])

            if not downloaded_file.endswith(".mp4"):
                video_status[video_id] = {"status": "converting"}
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i", downloaded_file,
                        "-c:v", "libx264",
                        "-crf", "51",
                        "-c:a", "aac",
                        "-strict", "experimental",
                        "-preset", "ultrafast",
                        "b:a", "64k",
                        "-movflags", "+faststart",
                        "-vf", "scale=854:480",
                        video_mp4_path
                    ],
                    check=True
                )
            else:
                shutil.copy(downloaded_file, video_mp4_path)

        if not os.path.exists(video_flv_path):
            video_status[video_id] = {"status": "converting for Wii"}
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", video_mp4_path,
                    "-ar", "22050",
                    "-f", "flv",
                    "-s", "320x240",
                    "-ab", "32k",
                    "-preset", "ultrafast",
                    "-crf", "51",
                    "-filter:v", "fps=fps=15",
                    video_flv_path
                ],
                check=True)

        video_status[video_id] = {"status": "complete", "url": f"/sigma/videos/{video_id}.mp4"}

    except Exception as e:
        video_status[video_id] = {"status": "error", "message": str(e)}

@app.route("/status/<video_id>")
def check_status(video_id):
    return jsonify(video_status.get(video_id, {"status": "pending"}))

@app.route("/video_metadata/<video_id>")
def video_metadata(video_id):
    api_key = get_api_key()

    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }

    try:
        response = requests.get(YOUTUBE_API_URL, params=params, timeout=1)
        response.raise_for_status()  

        data = response.json()

        if "items" not in data or len(data["items"]) == 0:
            return f"Video mit ID {video_id} wurde nicht gefunden.", 404

        video_data = data["items"][0]
        title = video_data["snippet"]["title"]
        description = video_data["snippet"]["description"]
        uploader = video_data["snippet"]["channelTitle"]
        channel_id = video_data["snippet"]["channelId"]
        view_count = video_data["statistics"].get("viewCount", "Unknown")
        like_count = video_data["statistics"].get("likeCount", "Unknown")
        dislike_count = video_data["statistics"].get("dislikeCount", "Unknown")
        published_at = video_data["snippet"].get("publishedAt", "Unknown")

        return {
            "title": title,
            "uploader": uploader,
            "channelId": channel_id,
            "description": description,
            "viewCount": view_count,
            "likeCount": like_count,
            "dislikeCount": dislike_count,
            "publishedAt": published_at
        }

    except requests.exceptions.RequestException as e:
        return f"Fehler bei der API-Anfrage: {str(e)}", 500

@app.route("/<path:filename>")
def serve_video(filename):
    file_path = os.path.join(filename)

    if not os.path.exists(file_path):
        return "File not found.", 404

    file_size = get_file_size(file_path)

    range_header = request.headers.get('Range', None)
    if range_header:
        byte_range = range_header.strip().split('=')[1]
        start_byte, end_byte = byte_range.split('-')
        start_byte = int(start_byte)
        end_byte = int(end_byte) if end_byte else file_size - 1

        if start_byte >= file_size or end_byte >= file_size:
            abort(416)  

        data = get_range(file_path, (start_byte, end_byte))
        content_range = f"bytes {start_byte}-{end_byte}/{file_size}"

        response = Response(
            data,
            status=206,
            mimetype="video/mp4",
            content_type="video/mp4",
            direct_passthrough=True
        )
        response.headers["Content-Range"] = content_range
        response.headers["Content-Length"] = str(len(data))
        return response

    return send_file(file_path)

@app.route('/channel', methods=['GET'])
def channel_m():
    channel_id = request.args.get('channel_id', None)
    
    if not channel_id:
        return "Channel ID is required.", 400

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': 20,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/channel/{channel_id}/videos"
            info = ydl.extract_info(url, download=False)
            
            if 'entries' not in info:
                return "No videos found.", 404
            
            results = [
                {
                    'id': video['id'],
                    'title': video['title'],
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': f"http://yt.old.errexe.xyz/thumbnail/{video['id']}"
                }
                for video in info['entries']
            ]
            
            return render_template_string(INDEX_TEMPLATE, results=results)
    
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)