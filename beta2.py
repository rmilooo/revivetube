from flask import Flask, request, render_template_string, send_file, Response, abort
import tempfile
import shutil
import yt_dlp
import requests
import subprocess
import os
import threading
import time

# Flask-Setup
app = Flask(__name__)

# Konstanten
RIITUBE_BASE_URL = "https://riitube.rc24.xyz/"
VIDEO_FOLDER = "sigma/videos"
API_BASE_URL = "https://y.com.sb/api/v1/"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"

# Diese Funktion dient dazu, die Dateigröße zu ermitteln
def get_file_size(file_path):
    return os.path.getsize(file_path)

# Diese Funktion dient dazu, einen bestimmten Abschnitt einer Datei zurückzugeben
def get_range(file_path, byte_range):
    with open(file_path, 'rb') as f:
        f.seek(byte_range[0])
        return f.read(byte_range[1] - byte_range[0] + 1)

def get_api_key():
    try:
        with open("token.txt", "r") as f:
            return f.read().strip()  # Den API Key zurückgeben
    except FileNotFoundError:
        raise FileNotFoundError("Die Datei token.txt wurde nicht gefunden. Bitte stelle sicher, dass sie vorhanden ist.")

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
        time.sleep(86400)  # 24 hours
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
    <p style="font-size: 12px;">We are NOT afiliated with Nintendo or YouTube. This app is using Code from Wiinet.xyz.</p>
    <p style="color: blue">It's recommend to bookmark this Page</p>
    <p>It's normal that Sites take long to load</p>
    <p>Version: v0.0.9 Beta</p>
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
</head>
<body style="text-align: center; font-family: Arial, sans-serif;">
    <h1>{{ title }}</h1>
    <h3>Uploaded by: {{ uploader }}</h3>
    <video width="640" height="360" controls>
        <source src="{{ video_mp4 }}" type="video/mp4">
        Your browser does not support the video tag.
    </video>
    <h3>Description:</h3>
    <p>{{ description }}</p>
<script>
alert("This App is designed for the Nintendo Wii, some Vidoes will not work!");
</script>
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
</head>
<body style="text-align: center; font-family: Arial, sans-serif;">
    <div style="width: 100%; background-color: #000; text-align: center;">
        <object type="application/x-shockwave-flash" data="/player.swf" width="384" height="256">
            <param name="wmode" value="transparent">
            <param name="allowFullScreen" value="false">
            <param name="flashvars" value="filename={{ video_flv }}">
        </object>
    </div>
    <p>If the video does not play smoothly, restart the Internet Channel by pressing the Home button and then Reset. It's a bug. It happens if you visit too many Sites</p>
    <h1>{{ title }}</h1>
    <h3>Uploaded by: {{ uploader }}</h3>
    <h3>Description:</h3>
    <p>{{ description }}</p>
</body>
</html>
"""
@app.route("/thumbnail/<video_id>")
def get_thumbnail(video_id):
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    try:
        # Thumbnail von YouTube abrufen
        response = requests.get(thumbnail_url, stream=True, timeout=5)
        if response.status_code == 200:
            # Content-Type weiterleiten
            return send_file(
                response.raw,
                mimetype=response.headers.get("Content-Type", "image/jpeg"),
                as_attachment=False,
            )
        else:
            return f"Failed to fetch thumbnail. Status: {response.status_code}", 500
    except requests.exceptions.RequestException as e:
        return f"Error fetching thumbnail: {str(e)}", 500

@app.route("/", methods=["GET"])
def index():
    query = request.args.get("query")
    results = None

    if query:
        # API-Anfrage an y.com.sb für die Suchergebnisse
        response = requests.get(f"{API_BASE_URL}search?q={query}", timeout=3)
        try:
            data = response.json()  # Parst die JSON-Antwort der API
        except ValueError:
            return "Fehler beim Parsen der API-Antwort.", 500

        # Ergebnisse verarbeiten, falls die API-Antwort erfolgreich und im erwarteten Format ist
        if response.status_code == 200 and isinstance(data, list):
            results = [
                {
                    "id": entry.get("videoId"),  # Die Video-ID
                    "title": entry.get("title"),  # Der Titel des Videos
                    "uploader": entry.get("author", "Unbekannt"),  # Der Name des Uploaders
                    "thumbnail": f"/thumbnail/{entry['videoId']}",
                    "viewCount": entry.get("viewCountText", "Unbekannt"),  # Anzahl der Aufrufe
                    "published": entry.get("publishedText", "Unbekannt")  # Veröffentlichungsdatum
                }
                for entry in data  # Iteriere durch jedes Video
                if entry.get("videoId")  # Sicherstellen, dass ein VideoID vorhanden ist
            ]
        else:
            return "Keine Ergebnisse gefunden oder Fehler in der API-Antwort.", 404

    return render_template_string(INDEX_TEMPLATE, results=results)

@app.route("/watch", methods=["GET"])
def watch():
    video_id = request.args.get("video_id")
    if not video_id:
        return "Fehlende Video-ID.", 400

    # Pfade für die Video-Dateien
    video_output_path = os.path.join(VIDEO_FOLDER, f"{video_id}.%(ext)s")  # Variable Erweiterung
    video_downloaded_path = None  # Platzhalter für die heruntergeladene Datei
    video_mp4_path = os.path.join(VIDEO_FOLDER, f"{video_id}.mp4")
    video_flv_path = os.path.join(VIDEO_FOLDER, f"{video_id}.flv")

    # Metadaten abrufen
    metadata_response = requests.get(f"http://127.0.0.1:5000/video_metadata/{video_id}")
    if metadata_response.status_code != 200:
        return f"Fehler beim Abrufen der Metadaten: {metadata_response.text}", 500

    metadata = metadata_response.json()

    # User-Agent prüfen
    user_agent = request.headers.get("User-Agent", "").lower()
    is_wii = "wii" in user_agent and "wiiu" not in user_agent

    # Video herunterladen, falls nicht vorhanden
    if not os.path.exists(video_mp4_path):
        try:
            # Erstelle ein temporäres Verzeichnis für die Konvertierung
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_video_path = os.path.join(temp_dir, f"{video_id}.%(ext)s")

                # yt-dlp-Command zum Herunterladen des Videos
                command = [
                    "yt-dlp",
                    "-o", temp_video_path,
                    f"https://m.youtube.com/watch?v={video_id}"  # Video-URL
                ]
                subprocess.run(command, check=True)

                # Finden der heruntergeladenen Datei
                downloaded_files = [f for f in os.listdir(temp_dir) if f.startswith(video_id)]
                if downloaded_files:
                    video_downloaded_path = os.path.join(temp_dir, downloaded_files[0])
                else:
                    return "Heruntergeladene Datei nicht gefunden.", 500

                # Prüfen, ob die heruntergeladene Datei bereits im MP4-Format ist
                if video_downloaded_path.endswith(".mp4"):
                    # Wenn die Datei im MP4-Format vorliegt, wird keine Konvertierung durchgeführt
                    # Kopiere die MP4-Datei in das endgültige Verzeichnis
                    shutil.copy(video_downloaded_path, video_mp4_path)
                else:
                    # Konvertierung zu MP4 mit modernen Codecs
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-i", video_downloaded_path,   # Eingabedatei
                            "-c:v", "libx264",            # H.264 Video-Codec
                            "-c:a", "aac",                # AAC Audio-Codec
                            "-strict", "experimental",
                            "-preset", "fast",            # Schnelles Encoding
                            "-movflags", "+faststart",    # Optimierung für Streaming
                            "-vf", "scale=854:480",       # Auflösung auf 480p setzen
                            video_mp4_path                # Ziel als MP4
                        ],
                        check=True
                    )

                    # Originaldatei nach der Konvertierung löschen
                    if video_downloaded_path != video_mp4_path:
                        os.remove(video_downloaded_path)

                    # Verschieben der konvertierten Datei ins endgültige Verzeichnis
                    if os.path.exists(video_mp4_path):
                        shutil.move(video_mp4_path, os.path.join(VIDEO_FOLDER, f"{video_id}.mp4"))

        except subprocess.CalledProcessError as e:
            return f"Fehler beim Herunterladen oder der Konvertierung des Videos: {e.stderr}", 500

    # Für Wii in FLV umwandeln, falls erforderlich
    if is_wii and not os.path.exists(video_flv_path):
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
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
            return f"Fehler bei der Konvertierung in FLV: {str(e)}", 500

    # HTML basierend auf User-Agent rendern
    if is_wii:
        return render_template_string(WATCH_WII_TEMPLATE, **metadata, video_flv=f"/sigma/videos/{video_id}.flv")
    else:
        return render_template_string(WATCH_STANDARD_TEMPLATE, **metadata, video_mp4=f"/sigma/videos/{video_id}.mp4")

# Video-Metadaten zurückgeben (Simulation für Metadaten)
@app.route("/video_metadata/<video_id>")
def video_metadata(video_id):
    api_key = get_api_key()

    # API-Anfrage an YouTube Data API v3
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }
    
    try:
        response = requests.get(YOUTUBE_API_URL, params=params, timeout=2)
        response.raise_for_status()  # Raise HTTPError für schlechte Antworten

        data = response.json()

        # Überprüfen, ob Video-Daten vorhanden sind
        if "items" not in data or len(data["items"]) == 0:
            return f"Video mit ID {video_id} wurde nicht gefunden.", 404

        # Metadaten extrahieren
        video_data = data["items"][0]
        title = video_data["snippet"]["title"]
        description = video_data["snippet"]["description"]
        uploader = video_data["snippet"]["channelTitle"]
        view_count = video_data["statistics"].get("viewCount", "Unknown")
        like_count = video_data["statistics"].get("likeCount", "Unknown")
        dislike_count = video_data["statistics"].get("dislikeCount", "Unknown")

        # Metadaten als JSON zurückgeben
        return {
            "title": title,
            "uploader": uploader,
            "description": description,
            "viewCount": view_count,
            "likeCount": like_count,
            "dislikeCount": dislike_count
        }

    except requests.exceptions.RequestException as e:
        return f"Fehler bei der API-Anfrage: {str(e)}", 500

@app.route("/<path:filename>")
def serve_video(filename):
    file_path = os.path.join(filename)

    # Überprüfen, ob die Datei existiert
    if not os.path.exists(file_path):
        return "File not found.", 404

    file_size = get_file_size(file_path)

    # Überprüfen, ob ein Range-Header vorhanden ist
    range_header = request.headers.get('Range', None)
    if range_header:
        # Range-Header parsen (Beispiel: 'bytes=0-499')
        byte_range = range_header.strip().split('=')[1]
        start_byte, end_byte = byte_range.split('-')
        start_byte = int(start_byte)
        end_byte = int(end_byte) if end_byte else file_size - 1

        # Wenn der angeforderte Bereich ungültig ist
        if start_byte >= file_size or end_byte >= file_size:
            abort(416)  # 416 Range Not Satisfiable

        # Abschnitt der Datei zurückgeben
        data = get_range(file_path, (start_byte, end_byte))
        content_range = f"bytes {start_byte}-{end_byte}/{file_size}"

        # Antwort mit Status 206 (Partial Content)
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

    # Wenn kein Range-Header vorhanden ist, wird die ganze Datei gesendet
    return send_file(file_path)

if __name__ == "__main__":
    app.run(debug=True)
