from fastapi import FastAPI, HTTPException, File, UploadFile, Response, Request, Query
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import shutil
import time
import re
from PIL import Image
from io import BytesIO
from auth_handler import auth_handler as auth
from plugin import Plugin

import os
import base64
import uuid
import json
import av
import psutil
from psutil import NoSuchProcess
import requests
import subprocess
import numpy as np
import sys
import importlib
from time import sleep
from huey import SqliteHuey
from huey.storage import SqliteStorage
from huey.constants import EmptyData
from huey.exceptions import TaskException
import sentry_sdk
from sentry_sdk.integrations.huey import HueyIntegration
from hashlib import md5
import sqlite3    
# from PySide6.QtWidgets import QApplication
import cv2
import io

import asyncio
from huey.exceptions import TaskException
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

UI_ENABLED = False

origins = [
    "http://deepmake.com",
    "https://deepmake.com",
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:8080",
    "*"
]

origin_regexes = [
    "http://.*\.deepmake\.com",
    "https://.*\.deepmake\.com",
]

CONDA = "MiniConda3"

def get_id(): # return md5 hash of uuid.getnode()
    return md5(str(uuid.getnode()).encode()).hexdigest()

sentry_sdk.init(
    dsn="https://d4853d3e3873643fa675bc620a58772c@o4506430643175424.ingest.sentry.io/4506463076614144",
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    enable_tracing=True,
    integrations=[
        HueyIntegration(),
    ],
)
user = {"id": get_id()}
sentry_sdk.set_tag("platform", sys.platform)
sentry_sdk.set_tag("os", sys.platform)
if auth.logged_in:
    user["email"] = auth.username
    user_info = auth.get_user_info()
    if "id" in user_info.keys():
        user["acct_id"] = user_info["id"]
sentry_sdk.set_user(user)

sentry_sdk.capture_message('Backend started')

global port_mapping
global plugin_endpoints
global storage_dictionary

if sys.platform == "win32":
    storage_folder = os.path.join(os.getenv('APPDATA'),"DeepMake")
elif sys.platform == "darwin":
    storage_folder = os.path.join(os.getenv('HOME'),"Library","Application Support","DeepMake")
elif sys.platform == "linux":
    storage_folder = os.path.join(os.getenv('HOME'),".local", "DeepMake")
# exit()

# storage_folder =  "/opt/dlami/nvme/DeepMake" # Set storage folder for AWS instances

if not os.path.exists(storage_folder):
    os.mkdir(storage_folder)

storage = SqliteStorage(name="storage", filename=os.path.join(storage_folder, 'huey_storage.db'))

huey = SqliteHuey(filename=os.path.join(storage_folder,'huey.db'))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if UI_ENABLED:
    from routers import ui, plugin_manager, report, login

    app.include_router(ui.router, tags=["ui"], prefix="/ui")
    app.include_router(plugin_manager.router, tags=["plugin_manager"], prefix="/plugin_manager")
    app.include_router(report.router, tags=["report"], prefix="/report")
    app.include_router(login.router, tags=["login"], prefix="/login")

client = requests.Session()

class Task(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

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
most_recent_use = []

plugin_info = {}

port_mapping = {"main": 8000}
process_ids = {}
plugin_endpoints = {}
plugin_memory = {}
PLUGINS_DIRECTORY = "plugin"

def fetch_image(img_id):
    img_data = storage.peek_data(img_id)
    if img_data == EmptyData:
        raise HTTPException(status_code=400, detail=f"No image found for id {img_id}")
    return img_data

@app.get("/get_main_pid/{pid}")
def get_main_pid(pid):
    if "main" in process_ids:
        return {"status": "failed", "error": "Already received a pid"}
    process_ids["main"] = int(pid)
    return {"status": "success"}

@app.on_event("startup")
def startup():
    reload_plugin_list()
    init_db()  # Initialize the database

    if sys.platform != "win32":
        p = subprocess.Popen("huey_consumer.py main.huey".split())
    else:
        huey_script_path = os.path.join(os.path.dirname(sys.executable), "Scripts\\huey_consumer.py")
        p = subprocess.Popen([sys.executable, huey_script_path, "main.huey"], shell=True)
    pid = p.pid

    process_ids["huey"] = pid

def init_db():
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS key_value_store (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

def reload_plugin_list():
    if "plugin_list" in globals():
        del globals()["plugin_list"]
        del globals()["plugin_states"]
    global plugin_list
    plugin_list=[]
    global plugin_states
    plugin_states = {}
    for folder in os.listdir(PLUGINS_DIRECTORY):
        # print(folder)
        if os.path.isdir(os.path.join(PLUGINS_DIRECTORY, folder)):
            if folder in plugin_list:
                pass
            elif "plugin.py" not in os.listdir(os.path.join(PLUGINS_DIRECTORY, folder)):
                pass
            else:
                plugin_list.append(folder)
                if folder not in plugin_states:
                    plugin_states[folder] = "INIT"
    # print(plugin_list)
    for plugin in list(plugin_states.keys()):
        if plugin not in plugin_list:
            if plugin in process_ids.keys():
                stop_plugin(plugin)
            del plugin_states[plugin]

async def serialize_image(image):
    image= base64.b64encode(await image.read())
    img_data = image.decode()
    return img_data

def store_image(img_data, img_id=None):
    if img_id is None:
      img_id = str(uuid.uuid4())
    #if not isinstance(img_data, bytes):
        #raise HTTPException(status_code=400, detail=f"Data must be stored in bytes")
    storage.put_data(img_id, img_data)
    return img_id

async def upload_store_image(data):
    img_data = await data.read()
    img_id = str(uuid.uuid4())
    storage.put_data(img_id,img_data)
    return img_id

def available_gpu_memory():
    command = "nvidia-smi --query-gpu=memory.free --format=csv"
    try:
        memory_free_info = subprocess.check_output(command.split()).decode('ascii').split('\n')[:-1][1:]
    except: 
        return -1
    memory_free_values = [int(x.split()[0]) for i, x in enumerate(memory_free_info)]
    return np.sum(memory_free_values)

def mac_gpu_memory():
    vm = subprocess.Popen(['vm_stat'], stdout=subprocess.PIPE).communicate()[0].decode()
    vmLines = vm.split('\n')
    sep = re.compile(':[\s]+')
    vmStats = {}
    page_size = int(vmLines[0].split(" ")[-2])
    for row in range(1,len(vmLines)-2):
        rowText = vmLines[row].strip()
        rowElements = sep.split(rowText)
        vmStats[(rowElements[0])] = int(rowElements[1].strip("\.")) * page_size /1024**2
    return vmStats["Pages free"] + vmStats["Pages inactive"]

def new_job(job):
    jobs[job.id] = job
    running_jobs.append(job.id)


def process_frame_with_plugin(img_id: str, prompt: str, port: int):
    response = requests.get(
        f"http://localhost:{port}/execute/{img_id}/{prompt}"
    )
    if response.status_code == 200:
        result = response.json()
        return result["output_mask"]
    else:
        raise HTTPException(status_code=500, detail="Error processing frame with plugin")

    
def process_frames_with_plugin(img_ids, prompt, plugin_port):
    url = f"http://localhost:{plugin_port}/execute_batch"
    data = {
        "img_ids": img_ids,
        "prompt": prompt
    }
    print(f"Sending data to plugin: {data}")  # Log the data being sent
    response = requests.post(url, json=data)
    if response.status_code != 200:
        print(f"Error processing frames with plugin: {response.text}")
        raise HTTPException(status_code=response.status_code, detail="Error processing frames with plugin")
    return response.json()["masks"]


@app.get("/")
async def redirect_docs():
    return RedirectResponse("/docs/")

@app.get("/plugins/reload")
async def reload_plugins():
    reload_plugin_list()
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
    try:
        r = auth.get_url("https://deepmake.com/plugins.json")
        store_data("plugin_info", r)
    except Exception as e:
        try:
            r = retrieve_data("plugin_info")
            # print("Can't connect to Internet, using cached file")
        except:
            r = {}

    json_exists = True
    try:
        r[plugin_name]
    except:
        json_exists = False
        
    if plugin_name in plugin_list: 
        if plugin_name not in plugin_info.keys():
            plugin = importlib.import_module(f"plugin.{plugin_name}.config", package = f'{plugin_name}.config')
            plugin_info[plugin_name] = {"plugin": plugin.plugin, "config": plugin.config, "endpoints": plugin.endpoints}
            plugin_endpoints[plugin_name] = plugin.endpoints
            # print(plugin_info[plugin_name]["plugin"]["memory"])
            if json_exists:
                initial_value = int(r[plugin_name]["vram"].split(" ")[0])
                mult = 1
                if "GB" in r[plugin_name]["vram"]:
                    mult = 1024
                initial_value *= mult
            else:
                initial_value = 1000
            store_data(f"{plugin_name}_memory", {"memory": [initial_value]})
            # store_data(f"{plugin_name}_model_memory", {"memory": plugin_info[plugin_name]["plugin"]["model_memory"]})
            store_data(f"{plugin_name}_memory_mean", {"memory": initial_value})
            store_data(f"{plugin_name}_memory_max", {"memory": initial_value})
            store_data(f"{plugin_name}_memory_min", {"memory": initial_value})

            try:
                plugin_info[plugin_name]["plugin"]["license"] = r[plugin_name]["license"]
            except:
                plugin_info[plugin_name]["plugin"]["license"] = 1 # Unknown plugins require a subscription to run
        return plugin_info[plugin_name]
    else:
        raise HTTPException(status_code=404, detail="Plugin not found")

@app.get("/plugins/get_config/{plugin_name}")
def get_plugin_config(plugin_name: str):
    if plugin_name in plugin_list:
        sleep = 0
        # while plugin_states[plugin_name] != "RUNNING":
        #     start_plugin(plugin_name)
        #     time.sleep(5)
        #     sleep += 5
        #     if sleep > 120:
        #         return {"status": "failed", "error": "Plugin too slow to start"}
        if plugin_name in port_mapping.keys():
            port = port_mapping[plugin_name]
            r = client.get("http://127.0.0.1:" + port + "/get_config")
            if r.status_code == 200:
                return r.json()
            else:
                return {"status": "failed", "error": r.text}
        else:
            try:
                # print(f"Getting config for {plugin_name}")
                # print(f"plugin_config.{plugin_name}")
                data = retrieve_data(f"plugin_config.{plugin_name}")
                # print(data)
                return data
            except Exception as e:
                # print(e)
                # print("Plugin config not found in DB, getting default")
                return get_plugin_info(plugin_name)["config"]
    else:
        raise HTTPException(status_code=404, detail="Plugin not found")

@app.put("/plugins/set_config/{plugin_name}")
def set_plugin_config(plugin_name: str, config: dict):
    if plugin_name in plugin_list:
        if plugin_name in port_mapping.keys():
            memory_func = available_gpu_memory if sys.platform != "darwin" else mac_gpu_memory
            available_memory = memory_func() 
            # current_model_memory = retrieve_data(f"{plugin_name}_model_memory")["memory"]
            # initial_memory = available_memory + current_model_memory
            # port = port_mapping[plugin_name]
            # r = client.put(f"http://127.0.0.1:{port}/set_config", json= config)
            job = huey_set_config(plugin_name, config, port_mapping)
            # after_memory = memory_func()
            # new_model_memory = initial_memory - after_memory
            # store_data(f"{plugin_name}_model_memory", {"memory": int(new_model_memory)})
            return {"job_id": job.id}
        else:
            try:
                original_config = retrieve_data(f"plugin_config.{self.plugin_name}")
            except:
                original_config = get_plugin_info(plugin_name)["config"]
            original_config.update(config)
            store_data(f"plugin_config.{plugin_name}", original_config)
    else:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
@huey.task()
def huey_set_config(plugin_name: str, config: dict, port_mapping):
    port = port_mapping[plugin_name]
    r = client.put(f"http://127.0.0.1:{port}/set_config", json= config)
    if r.status_code == 200:
        return r.json()
    else:
        raise TaskException(f"Failed to set config for {plugin_name}")

@app.get("/plugins/start_plugin/{plugin_name}")
async def start_plugin(plugin_name: str, port: int = None, min_port: int = 1001, max_port: int = 65534):
    if plugin_name not in plugin_info.keys():
        get_plugin_info(plugin_name)

    if plugin_name in port_mapping.keys():
        return {"started": True, "plugin_name": plugin_name, "port": port, "warning": "Plugin already running"}

    memory_func = available_gpu_memory if sys.platform != "darwin" else mac_gpu_memory
    
    # if plugin_name not in plugin_info.keys():
    #     get_plugin_info(plugin_name)
    
    available_memory = memory_func()

    if available_memory >= 0 and len(most_recent_use) > 0:
        if plugin_name in plugin_memory.keys():
            mem_usage = retrieve_data(f"{plugin_name}_memory_mean")["memory"]
            while mem_usage > available_memory and len(most_recent_use) > 0:
                plugin_to_shutdown = most_recent_use.pop()
                stop_plugin(plugin_to_shutdown)
                time.sleep(1)
                available_memory = memory_func() 
            
    store_data(f"{plugin_name}_available", {"memory": int(available_memory)})

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
            if os.getenv('CONDA_EXE'):
                conda_path = os.getenv('CONDA_EXE')
            elif sys.platform == "win32":
                conda_path = subprocess.check_output("echo %CONDA_EXE%", shell=True)[:-2].decode()
            else:
                conda_path = subprocess.check_output("echo $CONDA_EXE", shell=True)[:-2].decode()
            if not os.path.isfile(conda_path):
                conda_path = os.path.join(os.getenv('home'), "miniconda3", "Scripts", "conda.exe")
                activate_path = os.path.join(os.getenv('home'), "miniconda3", "Scripts", "activate.bat")
                p = subprocess.Popen(f"{activate_path}  && {conda_path} run -n {conda_env} uvicorn plugin.{plugin_name}.plugin:app --port {port}", shell=True)           
            else:
                p = subprocess.Popen(f"{conda_path} run -n {conda_env} uvicorn plugin.{plugin_name}.plugin:app --port {port}", shell=True)
        else:
            p = subprocess.Popen(f"envs\\plugins\\python.exe -m uvicorn plugin.{plugin_name}.plugin:app --port {port}", shell=True)
    pid = p.pid
    process_ids[plugin_name] = pid

    return {"started": True, "plugin_name": plugin_name, "port": port}

@app.get("/plugins/stop_plugin/{plugin_name}")
def stop_plugin(plugin_name: str):
    # need some test to ensure open port
    if plugin_name in process_ids.keys():
        parent_pid = process_ids[plugin_name]   # my example
        try:
            parent = psutil.Process(parent_pid)
        except NoSuchProcess:
            return {"status": "Failed", "Reason": f"Failed to kill {parent_pid} for plugin {plugin_name}"}
        try:
            for child in parent.children(recursive=True):  # or parent.children() for recursive=False
                child.kill()
            parent.kill()
        except:
            return {"status": "Failed", "Reason": f"Failed to kill plugin {plugin_name}"}

        process_ids.pop(plugin_name)
        if plugin_name != "huey":
            port_mapping.pop(plugin_name)
            plugin_states[plugin_name] = "STOPPED"
        
    return {"status": "Success", "description": f"{plugin_name} stopped"}
    
@app.put("/plugins/call_endpoint/{plugin_name}/{endpoint}")
async def call_endpoint(plugin_name: str, endpoint: str, json_data: dict, priority: int = 0):
    try:
        print(f"Calling endpoint {endpoint} for plugin {plugin_name}, with data {json_data}")
    except:
        pass
    if plugin_name not in plugin_list:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")
    if plugin_name not in port_mapping.keys():
        # print(f"{plugin_name} not yet started, starting now")
        await start_plugin(plugin_name)
    if plugin_name not in plugin_endpoints.keys():
        # print(f"Plugin {plugin_name} not in plugin_endpoints")
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
    memory_func = available_gpu_memory if sys.platform != "darwin" else mac_gpu_memory
    available_memory = memory_func()

    job = huey_call_endpoint(plugin_name, endpoint, json_data, port_mapping, plugin_endpoints, priority=priority)
    store_data(f"{job.id}_available", {"memory": int(available_memory), "plugin": plugin_name, "plugin_states": plugin_states, "running_jobs": get_running_jobs()["running_jobs"]})
    if plugin_name in most_recent_use:
        most_recent_use.remove(plugin_name)
    most_recent_use.insert(0, plugin_name)
    if warnings != []:
        return {"job_id": job.id, "warnings": warnings}
    new_job(job)
    return {"job_id": job.id}

@huey.task()
def huey_call_endpoint(plugin_name: str, endpoint: str, json_data: dict, port_mapping, plugin_endpoints):
    result = client.get("http://127.0.0.1:8000/plugins/get_states") # Calls REST instead of directly because of missing global due to threading
    if result.status_code == 200:
        result = result.json()
    else:
        raise HTTPException(status_code=500, detail="Failed to get plugin states")
    counter = 0
    while result[plugin_name]["state"] != "RUNNING":
        sleep(10)
        result = client.get("http://127.0.0.1:8000/plugins/get_states")
        if result.status_code == 200:
            result = result.json()
        counter += 1
        if counter > 10:
            raise HTTPException(status_code=504, detail=f"Plugin {plugin_name} failed to start")
    else:
        port = result[plugin_name]["port"]
    endpoint = plugin_endpoints[plugin_name][endpoint]

    if "method" not in endpoint.keys():
        endpoint["method"] = "GET"
    if endpoint['method'] == 'GET':
        inputs_string = ""
        for input in [input for input in endpoint['inputs'] if "optional=true" not in endpoint['inputs'][input]]:
            if input not in json_data.keys():
                return {"status": "failed", "error": f"Missing required input {input}"}
            inputs_string += str(json_data[input]) + "/"

        for ct, input in enumerate([input for input in json_data.keys() if "optional=true" in endpoint['inputs'][input]]):
            if ct == 0:
                inputs_string += f"?{input}={str(json_data[input])}"
            else:
                inputs_string += f"&{input}={str(json_data[input])}"

        url = f"http://127.0.0.1:{port}/{endpoint['call']}/{inputs_string}"
        response = client.get(url, timeout=240)
        if response.status_code == 200:
            response = response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    elif endpoint['method'] == 'PUT':
        inputs_string = ""
        for ct, input in enumerate([input for input in json_data.keys() if "optional=true" in endpoint['inputs'][input]]):
            if ct == 0:
                inputs_string += f"?{input}={str(json_data[input])}"
            else:
                inputs_string += f"&{input}={str(json_data[input])}"
        url = f"http://127.0.0.1:{port}/{endpoint['call']}/{inputs_string}"
        response = client.put(url, json=json_data, timeout=240)
        if response.status_code == 200:
            response = response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported method: {endpoint['method']}")

    return response

@app.get("/plugin/status/")
def get_all_plugin_status():
    return {"plugin_states": plugin_states}
    
@app.get("/plugin/status/{plugin_name}")
def get_plugin_status(plugin_name: str):
    status = plugin_states.get(plugin_name, "PLUGIN NOT FOUND")
    return {"plugin_name": plugin_name, "status": status}

@app.post("/plugin_callback/{plugin_name}/{status}")
def plugin_callback(plugin_name: str, status: str):
    running = status == "True"
    current_state = plugin_states.get(plugin_name)
    if sys.platform != "darwin":
        memory_func = available_gpu_memory
    else:
        memory_func = mac_gpu_memory
    try:
        print(f"Callback received for plugin: {plugin_name}. Current state: {current_state}")
    except:
        pass
    if running:
        plugin_states[plugin_name] = "RUNNING"
        # print(f"{plugin_name} is now in RUNNING state")
        for plugin in plugin_states.keys():
            if plugin_states[plugin] == "STARTING" or len(running_jobs) > 0:
                return {"status": "success", "message": f"{plugin_name} is now in RUNNING state"}
        initial_memory = retrieve_data(f"{plugin_name}_available")["memory"]
        memory_left = memory_func()    
        model_memory = initial_memory - memory_left
        
        # store_data(f"{plugin_name}_model_memory", {"memory": int(model_memory)})
        # model_memory = store_data(f"{plugin_name}_model_memory")["memory"]

        return {"status": "success", "message": f"{plugin_name} is now in RUNNING state"}
    else:
        # print(f"{plugin_name} failed to start")
        plugin_states.pop(plugin_name)
        return {"status": "error", "message": f"{plugin_name} failed to start because {status}"}

@app.post("/plugin_install_callback/{plugin_name}/{progress}/{stage}")
async def plugin_install_callback(plugin_name: str, progress: float, stage: str):
    # Handle installation progress update here
    # print(f"Installation progress for {plugin_name}: {progress}% complete. Current stage: {stage}")
    return {"status": "success", "message": f"Received installation progress for {plugin_name}"}

@app.post("/plugin_uninstall_callback/{plugin_name}/{progress}/{stage}")
async def plugin_uninstall_callback(plugin_name: str, progress: float, stage: str):
    # Handle uninstallation progress update here
    # print(f"Unistallation progress for {plugin_name}: {progress}% complete. Current stage: {stage}")
    return {"status": "success", "message": f"Received uninstallation progress for {plugin_name}"}

@app.get("/plugins/get_jobs")
def get_running_jobs():
    for job in running_jobs:
        try:
            job = jobs[job]
            if job() is not None:
                move_job(job.id)
        except Exception as e:
            if isinstance(e, TaskException):
                move_job(job.id)
    return {"running_jobs": running_jobs, "finished_jobs": finished_jobs}

@app.get("/backend/shutdown")
def shutdown():
    for plugin_name in list(process_ids.keys()):
        stop_plugin(plugin_name)
    
    if os.path.exists(os.path.join(storage_folder, "huey")):
        shutil.rmtree(os.path.join(storage_folder, "huey"))
    if os.path.exists(os.path.join(storage_folder, "huey_storage")):
        shutil.rmtree(os.path.join(storage_folder, "huey_storage"))
    if os.path.exists(os.path.join(storage_folder, "huey.db")):
        try:
            os.remove(os.path.join(storage_folder, "huey.db"))
        except PermissionError:
            # print("Failed to remove huey.db")
            pass

    stop_plugin("main")

@app.on_event("shutdown")
async def shutdown_event():
    for plugin_name in list(process_ids.keys()):
        stop_plugin(plugin_name)
    
    if os.path.exists(os.path.join(storage_folder, "huey")):
        shutil.rmtree(os.path.join(storage_folder, "huey"))
    if os.path.exists(os.path.join(storage_folder, "huey_storage")):
        shutil.rmtree(os.path.join(storage_folder, "huey_storage"))
    if os.path.exists(os.path.join(storage_folder, "huey.db")):
        try:
            os.remove(os.path.join(storage_folder, "huey.db"))
        except PermissionError:
            # print("Failed to remove huey.db")
            pass

@app.put("/job")
def add_job(job: Job):
    print("Received Job Payload:", job.dict())  # Print the received payload
    new_job(job)
    return {"message": f"Job {job.message_id} added"}

@huey.post_execute()
def record_memory(task, task_value, exc):
    if task_value is not None:
        try:
            task_data = retrieve_data(f"{task.id}_available")
        except:
            return

        plugin_states = task_data["plugin_states"]
        running_jobs = task_data["running_jobs"]
        for plugin in plugin_states.keys():
            if plugin_states[plugin] == "STARTING" or len(running_jobs) > 1:
                return task_value
        initial_memory = task_data["memory"]
        plugin_name = task_data["plugin"]
        # plugin_model_memory = retrieve_data(f"{plugin_name}_model_memory")["memory"]

        memory_func = available_gpu_memory if sys.platform != "darwin" else mac_gpu_memory
        memory_left = memory_func()
        # inference_memory = int(initial_memory - memory_left + plugin_model_memory)
        inference_memory = int(initial_memory - memory_left)

        mem_list = retrieve_data(f"{plugin_name}_memory")["memory"]
        mem_list.append(inference_memory)
        store_data(f"{plugin_name}_memory", {"memory": mem_list})
        store_data(f"{plugin_name}_memory_mean", {"memory": int(np.mean(mem_list))})
        store_data(f"{plugin_name}_memory_max", {"memory": int(np.max(mem_list))})
        store_data(f"{plugin_name}_memory_min", {"memory": int(np.min(mem_list))})
        delete_data(f"{task.id}_available")
        return task_value
    return task_value

def move_job(job_id):
    if job_id in running_jobs:
        
        running_jobs.remove(job_id) 
        finished_jobs.append(job_id)

@app.get("/job/{job_id}")
def get_job(job_id: str):
    try:
        job = jobs[job_id]
        if job() is None:
            return {"status": "Job in progress"}
    except Exception as e:
        if isinstance(e, KeyError):
            return {"status": "Job not found"}
    # print("moving job")
    move_job(job_id)
    # print("found job")
    try:
        result = job()
    except TaskException as e:
        return {"status": "Job failed", "detail": str(e)}
    return result

@app.get("/image/get/{img_id}")
async def get_img(img_id: str):
    image_bytes = fetch_image(img_id)
    return Response(content=image_bytes, media_type="image/png")

@app.post("/image/upload")
async def upload_img(file: UploadFile):
    # serialized_image = await serialize_image(file)
    image_id = await upload_store_image(file)
    return {"status": "Success", "image_id": image_id}

@app.post("/image/upload_multiple")
async def upload_images(files: list[UploadFile]):
    image_id = await store_multiple_images(files)
    return {"status": "Success", "image_id": image_id}

async def store_multiple_images(data):
    img_data = []
    for image in data:
        image_bytes = await image.read()
        img_data.append(Image.open(BytesIO(image_bytes)))
    shape = np.array(img_data).shape
    img_data = np.array(img_data).tobytes()
    img_id = str(uuid.uuid4())
    shape_id = img_id + "_shape"
    storage.put_data(img_id,img_data)
    storage.put_data(shape_id, np.array(shape).tobytes())
    return img_id

@app.post("/video/upload/", tags=["video"])
async def upload_video(request: Request, file: UploadFile = File(...)):
    # Print request headers for debugging
    print(f"Request headers: {request.headers}")
    print(f"Content type: {request.headers['content-type']}")
    
    # Print file details
    print(f"Filename: {file.filename}")
    print(f"Content type: {file.content_type}")

    # # Generate a unique ID for the video
    # video_id = str(uuid.uuid4())
    # Hask the video file and use as video ID
    print(f"Hashing video file to generate video ID")
    video_id = str(md5(file.file.read()).hexdigest())
    file.file.seek(0)
    video = av.open(file.file)
    # Get video height and width
    video_height = video.streams.video[0].height
    video_width = video.streams.video[0].width
    number_of_frames = video.streams.video[0].frames
    video.close()
    file.file.seek(0)

    metadata = {"height": video_height, "width": video_width, "frames": number_of_frames}
    # store video metadata in database
    store_data(video_id+"_metadata", metadata)

    print(f"Video ID: {video_id}") 
    video_path = os.path.join(storage_folder, f"{video_id}.mp4")

    # Save the uploaded video file
    with open(video_path, "wb") as video_file:
        shutil.copyfileobj(file.file, video_file)

    # Enqueue background task to process frames
    huey_enqueue_process_frames(video_path, video_id)

    # Return success response with video ID
    return {"status": "Success", "video_id": video_id, "metadata": metadata}

async def extract_frames(video_path: str, video_id: str):
    try:
        cap = cv2.VideoCapture(video_path)
        pts_to_frame_number = {}
        frames = []
        metadata = {"include_points": {}, "exclude_points": {}, "masks": {}, "image_ids": {}, "keyframes": {}}

        frame_number = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            pts = cap.get(cv2.CAP_PROP_POS_MSEC)
            pts_to_frame_number[pts] = frame_number

            # Convert frame to UploadFile
            is_success, buffer = cv2.imencode(".png", frame)
            if not is_success:
                continue
            img_bytes = io.BytesIO(buffer).getvalue()
            #img_file = UploadFile(file=io.BytesIO(img_bytes), filename=f"frame_{frame_number}.png")

            img_id = f"{video_id}_{frame_number}"

            # Store image and get image ID
            image_id = store_image(img_bytes, img_id)
            metadata["image_ids"][f"frame_{frame_number}"] = image_id

            frames.append(frame)
            # if frame_number % 30 == 0:  # Store keyframes
            #     keyframes.append(frame)

            frame_number += 1

        cap.release()

        frames_array = np.array(frames)
        # keyframes_array = np.array(keyframes)
        if not os.path.exists(os.path.join(storage_folder, f"{video_id}.npz")):
            np.savez(os.path.join(storage_folder, f"{video_id}.npz"), frames=frames_array, pts_to_frame_number=pts_to_frame_number, metadata=metadata)
        else:
            pass
        print(f"Frames and keyframes saved for video ID: {video_id}")
        print(f"Total frames extracted: {frame_number}")
        print(f"Frames array shape: {frames_array.shape}")
        # print(f"Keyframes array shape: {keyframes_array.shape}")
    except Exception as e:
        print(f"Error extracting frames: {str(e)}")
        raise e


# Background task to process frames
@huey.task()
def huey_enqueue_process_frames(video_path: str, video_id: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(extract_frames(video_path, video_id))
    loop.close()

@app.get("/video/stream/{video_id}", tags=["video"])
def stream_video(video_id: str):
    video_path = os.path.join(storage_folder, f"{video_id}_masked.mp4")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")

    def iterfile():
        print(f"Streaming video file {video_path}")
        try:
            with open(video_path, mode="rb") as file_like:
                yield from file_like
        except Exception as e:
            print(f"Error streaming video file: {str(e)}")
            raise HTTPException(status_code=500, detail="Error streaming video file")

    return StreamingResponse(iterfile(), media_type="video/mp4")


@app.get("/video/pts/{video_id}/", tags=["video"])
async def get_pts(video_id: str):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading video data")

    pts_to_frame_number = npz_data["pts_to_frame_number"].item()

    return {"pts_to_frame_number": pts_to_frame_number}


@app.get("/video/frames/{video_id}/", tags=["video"])
async def get_video_frames(video_id: str, start_frame: int = Query(0), end_frame: int = Query(None)):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading video frames")

    frames = npz_data["frames"]
    metadata = npz_data["metadata"].item()

    # Adjust end_frame if None
    if end_frame is None:
        end_frame = len(frames)

    if start_frame < 0 or end_frame > len(frames) or start_frame >= end_frame:
        raise HTTPException(status_code=400, detail="Frame range out of bounds")

    img_ids = [metadata["image_ids"].get(f"frame_{frame_number}") for frame_number in range(start_frame, end_frame)]
    
    return {"img_ids": img_ids}

@app.get("/video/data/{video_id}/", tags=["video"])
async def get_video_data(video_id: str):
    video_metadata = retrieve_data(f"{video_id}_metadata")
    if video_metadata is None:
        raise HTTPException(status_code=404, detail="Video not found")

    frames_data = npz_data["metadata"].item()
    try: 
        npz_path = os.path.join(storage_folder, f"{video_id}.npz")
        npz_data = np.load(npz_path, allow_pickle=True)
        frames_metadata = frames_data.get("masks", {})

        for mask in frames_metadata:
            if "image" in frames_metadata[mask]:
                image = frames_metadata[mask]["image"]
                del frames_metadata[mask]["image"]
                try:
                    img_id = store_image(image, f"{video_id}_mask_{mask.replace('frame_', '')}")
                    frames_metadata[mask]["img_id"] = img_id
                except Exception as e:
                    print(f"Error storing image: {str(e)}")
    except Exception as e:
        print("No npz file found")
        frames_metadata = {}

    return {"metadata": frames_metadata, "video_data": video_metadata}

@app.get("/video/mask_frames/{video_id}/", tags=["video"])
async def get_mask_frames(video_id: str, start_frame: int = None, end_frame: int = None):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading video frames")

    metadata = npz_data["metadata"].item()
    frames_metadata = metadata.get("masks", {})

    if start_frame is None:
        start_frame = 0

    if end_frame is None:
        end_frame = len(frames_metadata)

    filtered_metadata = {key: value for key, value in frames_metadata.items() if start_frame <= int(key.split('_')[1]) < end_frame}

    for mask in filtered_metadata:
        if "image" in filtered_metadata[mask]:
            image = filtered_metadata[mask]["image"]
            del filtered_metadata[mask]["image"]
            try:
                img_id = store_image(image, f"{video_id}_mask_{mask.replace('frame_', '')}")
                filtered_metadata[mask]["img_id"] = img_id
            except Exception as e:
                print(f"Error storing image: {str(e)}")

    return {"metadata": filtered_metadata}

@app.post("/video/set_mask/{video_id}", tags=["video"])
async def set_mask(video_id: str, masks: dict):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading video frames")

    metadata = npz_data["metadata"].item()

    # Update metadata with new masks
    for frame_number, mask_data in masks.items():
        metadata["masks"][f"frame_{frame_number}"] = mask_data

    for mask in metadata["masks"]:
        if "img_id" in metadata["masks"][mask]:
            image_id = metadata["masks"][mask]["img_id"]
            image = fetch_image(image_id)
            metadata["masks"][mask]["img"] = image

    # Save updated metadata
    np.savez(npz_path, frames=npz_data["frames"], pts_to_frame_number=npz_data["pts_to_frame_number"].item(), metadata=metadata)

    return {"status": "Success"}

# Get keyframes and their effect settings
@app.get("/video/keyframes/{video_id}/", tags=["video"])
async def get_keyframes(video_id: str):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading keyframes")

    keyframes = npz_data["metadata"].item().get("keyframes", [])
    return {"keyframes": keyframes}
    # Assuming effect settings are stored separately
    #effect_settings = get_effect_settings_for_keyframes(video_id)
    #return {"keyframes": keyframes.tolist(), "effect_settings": effect_settings}

@app.put("/video/set_keyframes/{video_id}/", tags=["video"])
async def set_keyframes(video_id: str, new_keyframes: dict):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading video")
    
    metadata = npz_data["metadata"].item()
    
    keyframes = metadata.get("keyframes", {})
    keyframes.update(new_keyframes)
    metadata["keyframes"] = keyframes

    np.savez(npz_path, frames=npz_data["frames"], pts_to_frame_number=npz_data["pts_to_frame_number"].item(), metadata=metadata)
    return({"status": "Success"})

@app.get("/video/export_masks/{video_id}/", tags=["video"])
async def export_masks(video_id: str, masked_video: bool = False):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_metadata = retrieve_data(f"{video_id}_metadata")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
        print(f"Loaded npz data for video ID: {video_id}")
    except Exception as e:
        print(f"Error loading npz data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading video frames")

    metadata = npz_data["metadata"].item().get("masks", {})
    video_folder = os.path.join(storage_folder, "export", video_id)
    if os.path.exists(video_folder):
        shutil.rmtree(video_folder)
    os.mkdir(video_folder)

    try:
        video_data = retrieve_data(f"{video_id}_metadata")
    except Exception as e:
        print(f"Error loading video metadata: {str(e)}")

    for frame_name in metadata.keys():
        frame = metadata[frame_name]
        frame_number = frame_name.replace("frame_", "")
        for maskname in frame.keys():
            mask = frame[maskname]
            if type(mask) != dict:
                continue
            if "img_id" in mask:
                if not os.path.exists(os.path.join(video_folder, maskname.replace(" ", "_"))):
                    # Create a new folder for the mask
                    os.mkdir(os.path.join(video_folder, maskname.replace(" ", "_")))
                    if masked_video:
                        os.mkdir(os.path.join(video_folder, maskname.replace(" ", "_")+"_masked"))
                try:
                    mask_image = Image.open(BytesIO(fetch_image(mask["img_id"])))
                except Exception as e:
                    print(f"Error fetching image: {str(e)} for mask {maskname}, frame {frame_number}, img_id {mask['img_id']}")
                    continue
                filename = os.path.join(video_folder, maskname.replace(" ", "_"), f"{frame_number.zfill(5)}.png")
                mask_image.save(filename)
                if masked_video:
                    original_image = np.asarray(Image.open(BytesIO(fetch_image(video_id + "_" + frame_number))))
                    masked_image = np.where(np.repeat(np.expand_dims(np.asarray(mask_image), axis=2), 3, axis=2) > 0, original_image, 0)
                    masked_filename = os.path.join(video_folder, maskname.replace(" ", "_")+"_masked", f"{frame_number.zfill(5)}.png")
                    masked_image = Image.fromarray(masked_image).save(masked_filename)

    size = video_data["width"], video_data["height"]

    video_list = []
    blank_image = np.zeros((size[1], size[0], 3), dtype=np.uint8)

    for imgdir in sorted(os.listdir(os.path.join(video_folder))):
        if not os.path.isdir(os.path.join(video_folder, imgdir)):
            continue
        video = cv2.VideoWriter(os.path.join(video_folder, f"{imgdir}.mp4"), cv2.VideoWriter_fourcc(*'mp4v'), 30, size)
        for framenum  in range(video_data["frames"]):
            img = f"{str(framenum).zfill(5)}.png"
            if os.path.exists(os.path.join(video_folder, imgdir, img)):
                try:
                    img = cv2.imread(os.path.join(video_folder, imgdir, img))
                    video.write(img)
                except:
                    video.write(blank_image)
            else:
                video.write(blank_image)
        # for img in sorted(os.listdir(os.path.join(video_folder, imgdir))):
        #     video.write(cv2.imread(os.path.join(video_folder, imgdir, img)))
        video.release()
        video_list.append(f"{video_id}/{imgdir}")

    return {"status": "Success", "video_list": video_list}


@app.get("/video/download_masks/{video_id}/{mask_name}", tags=["video"])
async def download_masks(video_id: str, mask_name: str):
    if not os.path.exists(os.path.join(storage_folder, "export", video_id, mask_name+".mp4")):
        raise HTTPException(status_code=404, detail="Mask not found")
    
    forbidden = ["..", "/", "\\"]
    if any([x in mask_name for x in forbidden]):
        raise HTTPException(status_code=400, detail="Invalid mask name")
    if any([x in video_id for x in forbidden]):
        raise HTTPException(status_code=400, detail="Invalid video ID")

    return FileResponse(os.path.join(storage_folder, "export", video_id, mask_name+".mp4"), filename=f"{video_id}_{mask_name}.mp4")

# Import masks from a video or image sequence
@app.post("/video/import_masks/{video_id}/", tags=["video"])
async def import_masks(video_id: str, masks: List[UploadFile]):
    return({"status": "Failed" , "message": "Not implemented yet"})
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading video frames")

    # frames = npz_data["frames"]

    for i, mask_file in enumerate(masks):
        mask_data = await mask_file.read()
        mask = np.array(Image.open(BytesIO(mask_data)))
        # Integrate mask with frame here, e.g., save mask or apply to frame

    return {"status": "Success"}

@app.put("/plugins/video/call_endpoint/{plugin_name}/{endpoint}", tags=["video"])
async def call_video_endpoint(plugin_name: str, endpoint: str, video_id: str, json_data: dict, start_frame: int = Query(0), end_frame: int = Query(None)):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")
    if not os.path.exists(npz_path):
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading video frames")

    frames = npz_data["frames"]
    metadata = npz_data["metadata"].item()

    print(f"Total frames available: {len(frames)}")
    print(f"Requested start frame: {start_frame}, end frame: {end_frame}")

    # Adjust end_frame if None
    if end_frame is None:
        end_frame = len(frames)

    if start_frame < 0 or end_frame > len(frames) or start_frame >= end_frame:
        raise HTTPException(status_code=400, detail="Frame range out of bounds")
    
    job_list = []
    for framenumber in range(max(0,start_frame), end_frame):
        json_data['img'] = f'{video_id}_{framenumber}'
        response = await call_endpoint(plugin_name, endpoint, json_data)
        job_id = response["job_id"]
        print("Job ID:", job_id)
        job_list.append(job_id)

    return {"job_ids": job_list}

@app.put("/data/store/{key}")
def store_data(key: str, item: dict):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    value = json.dumps(dict(item))
    cursor.execute("REPLACE INTO key_value_store (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    return {"message": "Data stored successfully"}

@app.get("/data/retrieve/{key}")
def retrieve_data(key: str):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM key_value_store WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = json.loads(row[0])
        return data
    raise HTTPException(status_code=404, detail="Key not found")

@app.delete("/data/delete/{key}")
def delete_data(key: str):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM key_value_store WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    return {"message": "Data deleted successfully"}