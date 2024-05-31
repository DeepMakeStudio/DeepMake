import subprocess
import sys
import requests
import time
import uuid
from hashlib import md5
from datetime import datetime
import json
import os

client = requests.Session()
def get_id(): # return md5 hash of uuid.getnode()
    return md5(str(uuid.getnode()).encode()).hexdigest()

def get_id(): # return md5 hash of uuid.getnode()
    return md5(str(uuid.getnode()).encode()).hexdigest()

def send_sentry(message):
    # Your Sentry DSN
    DSN = "https://d4853d3e3873643fa675bc620a58772c@o4506430643175424.ingest.sentry.io/4506463076614144"

    # Extract the Sentry host and project ID from the DSN
    dsn_parsed = DSN.split('/')
    project_id = "4506463076614144"
    project_key = "d4853d3e3873643fa675bc620a58772c"
    sentry_host = dsn_parsed[2]

    # Generate a unique event ID
    event_id = uuid.uuid4().hex

    # Current timestamp
    timestamp = datetime.utcnow().isoformat()

    # Construct the event payload
    event_payload = {
        "event_id": event_id,
        "timestamp": timestamp,
        "level": "debug",
        "message": message,
        "user": {
            "id": get_id()
        },
        "tags": {
            "os": sys.platform
        }
    }
    envelope_header = {
        "event_id": event_id,
        "dsn": DSN
    }
    envelope_data = {
        "type": "event",
        "content_type": "application/json",
        "length": len(json.dumps(event_payload)),
        "filename": "application.log"
    }

    # Construct the envelope
    envelope = f"{json.dumps(envelope_header)}\n{json.dumps(envelope_data)}\n{json.dumps(event_payload)}".strip()

    # Sentry Envelope endpoint
    url = f"https://{sentry_host}/api/{project_id}/envelope/"

    # Construct the authentication header
    auth_header = f"Sentry sentry_key={project_key}, sentry_version=7"

    # Send the envelope
    response = requests.post(url, data=envelope, headers={"Content-Type": "application/x-sentry-envelope", "X-Sentry-Auth": auth_header})

    return response

if __name__ == "__main__":
    if sys.platform == "win32":
        config_path = os.path.join(os.path.expandvars("%appdata%"),"DeepMake/Config.json")
    elif sys.platform == "darwin":
        config_path = os.path.join(os.path.expanduser("~/Library/Application Support/DeepMake/Config.json"))
    else:
        send_sentry(f"Failed to start backend\nOS is invalid\n{sys.platform}")
        config_path = os.path.join(os.path.expanduser("~/.config/DeepMake/Config.json"))
    if not os.path.exists(config_path):
        send_sentry(f"Failed to start backend\nConfig file not found")
        raise Exception(f"Config file not found: {config_path}")
    config_data = json.load(open(config_path,'r'))
    try:
        command = config_data['Py_Environment'] + config_data['Startup_CMD']
    except Exception as e:
        send_sentry(f"Failed to start backend\nConfig file missing required fields\n{e}")
        raise e

    try:
        if sys.platform != "win32":
            main_proc = subprocess.Popen(command)
        else:
            main_proc = subprocess.Popen(command)
        pid = main_proc.pid
        time.sleep(5)
    except Exception as e:
        send_sentry(f"Failed to start backend\n{e}\nCommand: {command}")
        raise e
    
    try:
        r = client.get(f"http://127.0.0.1:8000/get_main_pid/{pid}")
        if r.status_code != 200:
            send_sentry(f"Failed to start backend\n{r.text}")
            raise Exception(f"Failed to start backend: {r.text}")
    except Exception as e:
        send_sentry(f"Failed to start backend\n{e}")
        raise e
    try:
        client.get("http://127.0.0.1:8000/backend/shutdown")
    except:
        pass
    send_sentry("Backend test successful")