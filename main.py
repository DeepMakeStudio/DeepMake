from fastapi import FastAPI, HTTPException, File, UploadFile, Response
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import shutil
import os
import base64
import uuid
import json
import psutil
import requests
import subprocess
import numpy as np
import sys
import importlib
from time import sleep
from huey import SqliteHuey
from huey.storage import SqliteStorage
from huey.constants import EmptyData

CONDA = True

global port_mapping
global plugin_endpoints
global storage_dictionary

app = FastAPI()

if sys.platform == "win32":
    storage_folder = os.path.join(os.getenv('APPDATA'),"DeepMake")
elif sys.platform == "darwin":
    storage_folder = os.path.join(os.getenv('HOME'),"Library","Application Support","DeepMake")

if not os.path.exists(storage_folder):
    os.mkdir(storage_folder)

storage = SqliteStorage(name="storage", filename=os.path.join(storage_folder, 'huey_storage.db'))

huey = SqliteHuey(filename=os.path.join(storage_folder,'huey.db'))

app = FastAPI()
client = requests.Session()

port_mapping = {"main": 8000}
process_ids = {}
plugin_endpoints = {}

PLUGINS_DIRECTORY = "plugin"

class Task(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class Plugin(BaseModel):
    id: str
    name: str
    tasks: List[Task] = []

class Job(BaseModel):
    id: str
    task: Task
    status: str = 'queued'
    created_at: datetime = datetime.now()
    description: Optional[str] = None

jobs = {}
finished_jobs = []
running_jobs = []
jobs = {}

plugin_info = {}

def fetch_image(img_id):
    img_data = storage.peek_data(img_id)
    if img_data == EmptyData:
        raise HTTPException(status_code=400, detail=f"No image found for id {img_id}")
    return img_data

@app.on_event("startup")
def startup():
    global plugin_list
    plugin_list = []
    load_plugins()
    global plugin_states
    plugin_states = {plugin: "INIT" for plugin in plugin_list}

def load_plugins():
    for folder in os.listdir(PLUGINS_DIRECTORY):
        if os.path.isdir(os.path.join(PLUGINS_DIRECTORY, folder)):
            if folder in plugin_list:
                continue
            if "plugin.py" not in os.listdir(os.path.join(PLUGINS_DIRECTORY, folder)):
                continue
            plugin_list.append(folder)

    if sys.platform != "win32":
        p = subprocess.Popen("huey_consumer.py main.huey".split())
    else:
        huey_script_path = os.path.join(os.path.dirname(sys.executable), "Scripts\\huey_consumer.py")
        p = subprocess.Popen([sys.executable, huey_script_path, "main.huey"], shell=True)
    pid = p.pid

    process_ids["huey"] = pid

async def serialize_image(image):
    image= base64.b64encode(await image.read())
    img_data = image.decode()
    return img_data

async def store_image(image):
    img_data = await image.read()
    img_id = str(uuid.uuid4())
    storage.put_data(img_id,img_data)
    return img_id

def new_job(job):
    jobs[job.id] = job
    running_jobs.append(job.id)

@app.get("/plugins/reload")
async def reload_plugins():
    load_plugins()
    return {"status": "success"}

@app.get("/plugins/get_list")
def get_plugin_list():
    return {"plugins": list(plugin_states)}

@app.get("/plugins/get_states")
def get_plugin_list():
    result = {}
    for plugin in plugin_states.keys():
        if plugin in port_mapping.keys():
            result[plugin] = {"state": plugin_states[plugin], "port": port_mapping[plugin]}
        else:
            result[plugin] = {"state": plugin_states[plugin]}
    return result

@app.get("/plugins/get_info/{plugin_name}")
def get_plugin_info(plugin_name: str):
    if plugin_name in plugin_list: 
        if plugin_name not in plugin_info.keys():
            plugin = importlib.import_module(f"plugin.{plugin_name}.config", package = f'{plugin_name}.config')
            plugin_info[plugin_name] = {"plugin": plugin.plugin, "config": plugin.config, "endpoints": plugin.endpoints}
            plugin_endpoints[plugin_name] = plugin.endpoints
        return plugin_info[plugin_name]
    else:
        raise HTTPException(status_code=404, detail="Plugin not found")

@app.get("/plugins/get_config/{plugin_name}")
def get_plugin_config(plugin_name: str):
    if plugin_name in plugin_list: 
        port = port_mapping[plugin_name]
        r = client.get("http://127.0.0.1:" + port + "/get_config")
        return r.json()
    else:
        raise HTTPException(status_code=404, detail="Plugin not found")

@app.put("/plugins/set_config/{plugin_name}")
def set_plugin_config(plugin_name: str, config: dict):
    if plugin_name in plugin_list:
        port = port_mapping[plugin_name]
        r = client.put(f"http://127.0.0.1:{port}/set_config", json= config)
        return r.json()
    else:
        raise HTTPException(status_code=404, detail="Plugin not found")

@app.get("/plugins/start_plugin/{plugin_name}")
async def start_plugin(plugin_name: str, port: int = None, min_port: int = 1001, max_port: int = 65534):
    if plugin_name not in plugin_info.keys():
        get_plugin_info(plugin_name)

    if plugin_name in port_mapping.keys():
        return {"started": True, "plugin_name": plugin_name, "port": port, "warning": "Plugin already running"}
    plugin_states[plugin_name] = "STARTING"
    if port is None:
        port = np.random.randint(min_port,max_port)
        while port in list(port_mapping.values()):
            port = np.random.randint(min_port,max_port)
    elif port in list(port_mapping.values()):
        return {"started": False, "error": "Port already in use"}
    port_mapping[plugin_name] = str(port)
    conda_env = plugin_info[plugin_name]["plugin"]["env"]
    if sys.platform != "win32":
        if CONDA:
            p = subprocess.Popen(f"conda run -n {conda_env} uvicorn plugin.{plugin_name}.plugin:app --port {port}".split())
        else:
            p = subprocess.Popen(f"envs\plugins\python -m uvicorn plugin.{plugin_name}.plugin:app --port {port}".split())
    else:
        if CONDA:
            conda_path = subprocess.check_output("echo %CONDA_EXE%", shell=True)[:-2].decode()
            p = subprocess.Popen(f"{conda_path} run -n {conda_env} uvicorn plugin.{plugin_name}.plugin:app --port {port}", shell=True)
        else:
            p = subprocess.Popen(f"envs\plugins\python.exe -m uvicorn plugin.{plugin_name}.plugin:app --port {port}", shell=True)
    pid = p.pid
    process_ids[plugin_name] = pid

    return {"started": True, "plugin_name": plugin_name, "port": port}

@app.get("/plugins/stop_plugin/{plugin_name}")
def stop_plugin(plugin_name: str):
    # need some test to ensure open port
    if plugin_name in process_ids.keys():
        parent_pid = process_ids[plugin_name]   # my example
        parent = psutil.Process(parent_pid)
        for child in parent.children(recursive=True):  # or parent.children() for recursive=False
            child.kill()
        parent.kill()
        
    return f"{plugin_name} stopped"

@app.on_event("shutdown")
async def shutdown_event():
    for plugin_name in process_ids.keys():
        stop_plugin(plugin_name)
    
    if os.path.exists(os.path.join(storage_folder, "huey")):
        shutil.rmtree(os.path.join(storage_folder, "huey"))
    if os.path.exists(os.path.join(storage_folder, "huey_storage")):
        shutil.rmtree(os.path.join(storage_folder, "huey_storage"))
    if os.path.exists(os.path.join(storage_folder, "huey.db")):
        os.remove(os.path.join(storage_folder, "huey.db"))
    if os.path.exists(os.path.join(storage_folder, "huey_storage.db")):
        os.remove(os.path.join(storage_folder, "huey_storage.db"))
    
@app.put("/plugins/call_endpoint/{plugin_name}/{endpoint}")
async def call_endpoint(plugin_name: str, endpoint: str, json_data: dict):
    print(f"Calling endpoint {endpoint} for plugin {plugin_name}, with data {json_data}")
    if plugin_name not in plugin_list:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")
    if plugin_name not in port_mapping.keys():
        print(f"{plugin_name} not yet started, starting now")
        await start_plugin(plugin_name)
    if plugin_name not in plugin_endpoints.keys():
        print(f"Plugin {plugin_name} not in plugin_endpoints")
        get_plugin_info(plugin_name)
    if endpoint not in plugin_endpoints[plugin_name].keys():
        raise HTTPException(status_code=404, detail=f"Endpoint {endpoint} does not exist for plugin {plugin_name}")
    for input in [input for input in plugin_endpoints[plugin_name][endpoint]['inputs'] if "optional=true" not in plugin_endpoints[plugin_name][endpoint]['inputs'][input]]:
        if input not in json_data.keys():
            raise HTTPException(status_code=400, detail=f"Missing mandatory input {input} for endpoint {endpoint}")
    warnings = []
    for input in list(json_data.keys()):
        if input not in plugin_endpoints[plugin_name][endpoint]['inputs'].keys():
            warnings.append(f"Input '{input}' not used by endpoint '{endpoint}'")
            del json_data[input]
    job = huey_call_endpoint(plugin_name, endpoint, json_data, port_mapping, plugin_endpoints)
    if warnings != []:
        return {"job_id": job.id, "warnings": warnings}
    new_job(job)
    return {"job_id": job.id}

@huey.task()
def huey_call_endpoint(plugin_name: str, endpoint: str, json_data: dict, port_mapping, plugin_endpoints):
    result = client.get("http://127.0.0.1:8000/plugins/get_states").json()
    counter = 0
    while result[plugin_name]["state"] != "RUNNING":
        sleep(10)
        result = client.get("http://127.0.0.1:8000/plugins/get_states").json()
        counter += 1
        if counter > 10:
            raise HTTPException(status_code=500, detail=f"Plugin {plugin_name} failed to start")
    else:
        port = result[plugin_name]["port"]
    endpoint = plugin_endpoints[plugin_name][endpoint]
    inputs_string = ""
    for input in [input for input in endpoint['inputs'] if "optional=true" not in endpoint['inputs'][input]]:
        if input not in json_data.keys():
            return {"status": "failed", "error": f"Missing required input {input}"}
        inputs_string += json_data[input] + "/"

    for ct, input in enumerate([input for input in json_data.keys() if "optional=true" in endpoint['inputs'][input]]):
        if ct == 0:
            inputs_string += f"?{input}={str(json_data[input])}"
        else:
            inputs_string += f"&{input}={str(json_data[input])}"

    url = f"http://127.0.0.1:{port}/{endpoint['call']}/{inputs_string}"

    response = client.get(url, timeout=120).json()
    return response

@app.get("/plugin/status/")
def get_all_plugin_status():
    return {"plugin_states": plugin_states}
    
@app.get("/plugin/status/{plugin_name}")
def get_plugin_status(plugin_name: str):
    status = plugin_states.get(plugin_name, "NOT FOUND")
    return {"plugin_name": plugin_name, "status": status}

@app.post("/plugin_callback/{plugin_name}/{status}")
def plugin_callback(plugin_name: str, status: str):
    status = status == "True"
    current_state = plugin_states.get(plugin_name)
    print(f"Callback received for plugin: {plugin_name}. Current state: {current_state}")

    if status:
        plugin_states[plugin_name] = "RUNNING"
        print(f"{plugin_name} is now in RUNNING state")
        return {"status": "success", "message": f"{plugin_name} is now in RUNNING state"}
    else:
        print(f"{plugin_name} failed to start")
        plugin_states.pop(plugin_name)
        return {"status": "error", "message": f"{plugin_name} failed to start"}
    return {"status": "error", "message": f"{plugin_name} wasn't in the STARTING state or doesn't exist"}

@app.get("/plugins/get_jobs")
def get_running_jobs():
    for job in running_jobs:
        try:
            jobs[job].get_result()
            move_job(job)
        except Exception as e:
            if isinstance(e, ResultMissing):
                continue
            elif isinstance(e, ResultFailure):
                move_job(job)
    return {"running_jobs": running_jobs, "finished_jobs": finished_jobs}

@app.put("/job")
def add_job(job: Job):
    print("Received Job Payload:", job.dict())  # Print the received payload
    new_job(job)
    return {"message": f"Job {job.message_id} added"}

def move_job(job_id):
    if job_id in running_jobs:
        running_jobs.remove(job_id) 
        finished_jobs.append(job_id)

@app.get("/job/{job_id}")
def get_job(job_id: str):
    print("getting job")
    try:
        job = jobs[job_id]
        if job() is None:
            return {"status": "Job in progress"}
    except Exception as e:
        if isinstance(e, KeyError):
            return {"status": "Job not found"}
    print("moving job")
    move_job(job_id)
    print("found job")
    return job()

@app.get("/image/get/{img_id}")
async def get_img(img_id: str):
    image_bytes = fetch_image(img_id)
    return Response(content=image_bytes, media_type="image/png")

@app.post("/image/upload")
async def upload_img(file: UploadFile = File(...)):
    # serialized_image = await serialize_image(file)
    image_id = await store_image(file)
    return {"status": "Success", "image_id": image_id}