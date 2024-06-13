# import uvicorn
# from main import app
import subprocess
import sys
import requests
import time
import uuid

client = requests.Session()

if __name__ == "__main__":
    if sys.platform != "win32":
        main_proc = subprocess.Popen(f"gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --access-logfile - --pid gunicorn_pid".split())
    else:
        main_proc = subprocess.Popen(f"gunicorn main:app --worker-class uvicorn.workers.UvicornWorker --access-logfile - --pid gunicorn_pid", shell=True)
    
    time.sleep(3)

    frontend_id = str(uuid.uuid4())
    r = client.get(f"http://127.0.0.1:8000/frontend/start/{frontend_id}")   