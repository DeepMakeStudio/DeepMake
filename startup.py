# import uvicorn
# from main import app
import subprocess
import sys
import requests
import time

client = requests.Session()

if __name__ == "__main__":
    if sys.platform != "win32":
        main_proc = subprocess.Popen(f"uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info".split())
    else:
        main_proc = subprocess.Popen(f"uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info", shell=True)
    
    pid = main_proc.pid
    time.sleep(3)
    r = client.get(f"http://127.0.0.1:8000/get_main_pid/{pid}")
# uvicorn.run("main:app", host="127.0.0.1", port=8000, log_level="info")