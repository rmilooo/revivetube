import os
import time
import subprocess

def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

def delete_files(folder_path, extensions):
    os.system('sudo pkill -f revivetube.py')
    process = subprocess.Popen(['sudo', 'nohup', 'python3', 'revivetube.py'])
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            if any(filename.lower().endswith(ext) for ext in extensions):
                filepath = os.path.join(dirpath, filename)
                try:
                    os.remove(filepath)
                except:
                    print("ERROR")

def monitor_folder(folder_path, size_limit_gb, check_interval):
    size_limit_bytes = size_limit_gb * 1024 * 1024 * 1024
    while True:
        folder_size = get_folder_size(folder_path)
        if folder_size > size_limit_bytes:
            delete_files(folder_path, [".flv", ".mp4"])
        time.sleep(check_interval)

if __name__ == "__main__":
    folder_to_monitor = "./sigma/videos/"
    size_limit = 7
    interval = 5

    monitor_folder(folder_to_monitor, size_limit, interval)
