import os
import time

def get_folder_size(folder_path):
    """Berechnet die Gesamtgröße eines Ordners in Bytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            # Nur existierende Dateien berücksichtigen
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

def delete_files(folder_path, extensions):
    """Löscht alle Dateien mit den angegebenen Erweiterungen im Ordner."""
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            if any(filename.lower().endswith(ext) for ext in extensions):
                filepath = os.path.join(dirpath, filename)
                try:
                    os.remove(filepath)
                    print(f"Gelöscht: {filepath}")
                except Exception as e:
                    print(f"Fehler beim Löschen von {filepath}: {e}")

def monitor_folder(folder_path, size_limit_gb, check_interval):
    """Überwacht einen Ordner und löscht bestimmte Dateien, wenn die Größe überschritten wird."""
    size_limit_bytes = size_limit_gb * 1024 * 1024 * 1024  # GB in Bytes umrechnen
    while True:
        folder_size = get_folder_size(folder_path)
        print(f"Ordnergröße: {folder_size / (1024 * 1024 * 1024):.2f} GB")
        if folder_size > size_limit_bytes:
            print("Größenlimit überschritten! Lösche .flv und .mp4 Dateien...")
            delete_files(folder_path, [".flv", ".mp4"])
        time.sleep(check_interval)

if __name__ == "__main__":
    # Pfad zum Überwachungsordner
    folder_to_monitor = "./sigma/videos/"
    # Größenlimit in GB
    size_limit = 7  # Geändert auf 7 GB
    # Intervall in Sekunden
    interval = 5

    # Überwachung starten
    monitor_folder(folder_to_monitor, size_limit, interval)