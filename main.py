from fastapi import FastAPI, HTTPException, File, UploadFile, Response
from fastapi.responses import RedirectResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import shutil
import time
import re
from PIL import Image
from io import BytesIO

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
import sentry_sdk
from sentry_sdk.integrations.huey import HueyIntegration
from hashlib import md5
import sqlite3    
from pyqt_gui_table import Window
from PyQt6.QtWidgets import QApplication
from qt_material import apply_stylesheet
from update_gui import Updater
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
sentry_sdk.set_user({"id": get_id()})
sentry_sdk.set_tag("platform", sys.platform)

global port_mapping
global plugin_endpoints
global storage_dictionary

if sys.platform == "win32":
    storage_folder = os.path.join(os.getenv('APPDATA'),"DeepMake")
elif sys.platform == "darwin":
    storage_folder = os.path.join(os.getenv('HOME'),"Library","Application Support","DeepMake")
elif sys.platform == "linux":
    storage_folder = os.path.join(os.getenv('HOME'),".local", "DeepMake")

if not os.path.exists(storage_folder):
    os.mkdir(storage_folder)

storage = SqliteStorage(name="storage", filename=os.path.join(storage_folder, 'huey_storage.db'))

huey = SqliteHuey(filename=os.path.join(storage_folder,'huey.db'))

app = FastAPI()
client = requests.Session()

port_mapping = {"main": 8000}
process_ids = {}
plugin_endpoints = {}
plugin_memory = {"Diffusers": 4000, "GroundingDINO": 3000, "Bisenet": 400, "Baseline": 0}

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
most_recent_use = []

plugin_info = {}

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
    global plugin_list
    plugin_list = []
    load_plugins()
    global plugin_states
    plugin_states = {plugin: "INIT" for plugin in plugin_list}
    init_db()  # Initialize the database

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

async def store_image(data):
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

@app.get("/")
async def redirect_docs():
    return RedirectResponse("/docs/")

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
    if sys.platform != "darwin":
        memory_func = available_gpu_memory
    else:
        memory_func = mac_gpu_memory
    
    available_memory = memory_func()
    if available_memory >= 0 and len(most_recent_use) > 0:
        if plugin_name in plugin_memory.keys():
            while plugin_memory[plugin_name] > available_memory and len(most_recent_use) > 0:
                plugin_to_shutdown = most_recent_use.pop()
                stop_plugin(plugin_to_shutdown)
                time.sleep(1)
                available_memory = memory_func() 
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
        parent = psutil.Process(parent_pid)
        for child in parent.children(recursive=True):  # or parent.children() for recursive=False
            child.kill()
        parent.kill()
        process_ids.pop(plugin_name)
        if plugin_name != "huey":
            port_mapping.pop(plugin_name)
            plugin_states[plugin_name] = "STOPPED"
        
    return f"{plugin_name} stopped"
    
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
    if plugin_name in most_recent_use:
        most_recent_use.remove(plugin_name)
    most_recent_use.insert(0, plugin_name)
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

    response = client.get(url, timeout=240).json()
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
    running = status == "True"
    current_state = plugin_states.get(plugin_name)
    print(f"Callback received for plugin: {plugin_name}. Current state: {current_state}")

    if running:
        plugin_states[plugin_name] = "RUNNING"
        print(f"{plugin_name} is now in RUNNING state")
        return {"status": "success", "message": f"{plugin_name} is now in RUNNING state"}
    else:
        print(f"{plugin_name} failed to start")
        plugin_states.pop(plugin_name)
        return {"status": "error", "message": f"{plugin_name} failed to start because {status}"}

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

@app.get("/backend/shutdown")
def shutdown():
    for plugin_name in list(process_ids.keys()):
        stop_plugin(plugin_name)
    
    if os.path.exists(os.path.join(storage_folder, "huey")):
        shutil.rmtree(os.path.join(storage_folder, "huey"))
    if os.path.exists(os.path.join(storage_folder, "huey_storage")):
        shutil.rmtree(os.path.join(storage_folder, "huey_storage"))
    if os.path.exists(os.path.join(storage_folder, "huey.db")):
        os.remove(os.path.join(storage_folder, "huey.db"))
    if os.path.exists(os.path.join(storage_folder, "huey_storage.db")):
        os.remove(os.path.join(storage_folder, "huey_storage.db"))
    
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
        os.remove(os.path.join(storage_folder, "huey.db"))
    if os.path.exists(os.path.join(storage_folder, "huey_storage.db")):
        os.remove(os.path.join(storage_folder, "huey_storage.db"))

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
    # print("moving job")
    move_job(job_id)
    # print("found job")
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

@app.put("/data/store/{key}")
async def store_data(key: str, item: dict):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    value = json.dumps(dict(item))
    cursor.execute("REPLACE INTO key_value_store (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    return {"message": "Data stored successfully"}

@app.get("/data/retrieve/{key}")
async def retrieve_data(key: str):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM key_value_store WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    data = json.loads(row[0])
    if row:
        return data
    raise HTTPException(status_code=404, detail="Key not found")

@app.delete("/data/delete/{key}")
async def delete_data(key: str):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM key_value_store WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    return {"message": "Data deleted successfully"}

@app.get("/ui/plugin_manager")
def plugin_manager():
    
    app = QApplication(sys.argv)
    window = Window()
    apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")
    window.setStyleSheet("QScrollBar::handle {background: #ffffff;} QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background: #ffffff;} QTableView {background-color: rgba(239,0,86,0.5); font-weight: bold;} QHeaderView::section {font-weight: bold; background-color: #7b3bff; color: #ffffff} QTableView::item:selected {background-color: #7b3bff; color: #ffffff;} QPushButton:pressed {color: #ffffff; background-color: #7b3bff;} QPushButton {color: #ffffff;}")
    window.show()
    try:
        sys.exit(app.exec())
    except:
        pass

@app.get("/ui/update")
def update():
    
    app = QApplication(sys.argv)
    window = Updater()
    apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")
    window.setStyleSheet("QScrollBar::handle {background: #ffffff;} QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background: #ffffff;} QTableView {background-color: rgba(239,0,86,0.5); font-weight: bold;} QHeaderView::section {font-weight: bold; background-color: #7b3bff; color: #ffffff} QTableView::item:selected {background-color: #7b3bff; color: #ffffff;} QPushButton:pressed {color: #ffffff; background-color: #7b3bff;} QPushButton {color: #ffffff;}")
    window.show()
    try:
        sys.exit(app.exec())
    except:
        pass