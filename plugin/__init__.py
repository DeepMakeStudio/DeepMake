from fastapi import HTTPException
import uuid
import requests
from huey.storage import FileStorage, SqliteStorage
import huey
import os
import sys
import numpy as np
from io import BytesIO
from PIL import Image
from tqdm import tqdm
import shutil
import threading
import sqlite3
import json
from redis import Redis
from config import storage_mode

if sys.platform == "win32":
    storage_folder = os.path.join(os.getenv('APPDATA'),"DeepMake")
elif sys.platform == "darwin":
    storage_folder = os.path.join(os.getenv('HOME'),"Library","Application Support","DeepMake")
elif sys.platform == "linux":
    storage_folder = os.path.join(os.getenv('HOME'),".local", "DeepMake")

# storage_folder =  "/opt/dlami/nvme/DeepMake" # Set storage folder for AWS instances

if not os.path.exists(storage_folder):
    os.mkdir(storage_folder)

if storage_mode == "local":
    storage = SqliteStorage(name="storage", filename=os.path.join(storage_folder, 'huey_storage.db'))
elif storage_mode == "aws":
    from config import aws_endpoint
    print("On AWS")
    storage = Redis(host=aws_endpoint, port=6379, ssl=True)

print(storage_folder)

def fetch_image(img_id):
    if storage_mode == "local":
        img_data = storage.peek_data(img_id)
        if img_data == huey.constants.EmptyData:
            raise HTTPException(status_code=400, detail=f"No image found for id {img_id}")
    elif storage_mode == "aws":
        img_data = storage.get(img_id)
    return img_data

def fetch_pil_image(img_id):
    img_data = fetch_image(img_id)
    return Image.open(BytesIO(img_data))

def store_pil_image(img, img_id=None):
    output = BytesIO()
    img.save(output, format="PNG")
    img_data = output.getvalue()
    return store_image(img_data, img_id)


def store_image(img_data, img_id=None):
    if img_id is None:
      img_id = str(uuid.uuid4())
    #if not isinstance(img_data, bytes):
        #raise HTTPException(status_code=400, detail=f"Data must be stored in bytes")
    if storage_mode == "local":
        storage.put_data(img_id, img_data)
    elif storage_mode == "aws":
        storage.set(img_id, img_data)
    return img_id

def store_multiple_images(img_data):
    video_id = str(uuid.uuid4())

    img_id_list = [store_image(img_data[i], video_id + f"_{i}") for i in range(len(img_data))]
    bytes_list = bytes(";".join(img_id_list).encode("utf-8"))
    storage.put_data(video_id, bytes_list)
    return video_id

def store_multiple(data_list, func, img_ids=None):
    list_id = str(uuid.uuid4())
    if img_ids is None:
        img_ids = [func(img) for img in data_list]
    elif len(data_list) == len(img_ids):
        img_ids = [func(img, img_id) for img, img_id in zip(data_list, img_ids)]
    elif type(img_ids) == str:
        img_ids = [func(img, img_ids + str(i)) for i, img in enumerate(data_list)]
    bytes_list = bytes(";".join(img_ids).encode("utf-8"))
    storage.put_data(list_id, bytes_list)
    return list_id

def fetch_multiple(func, id_list):
    return [func(img_id) for img_id in id_list]

def get_video(video_id: str):
    npz_path = os.path.join(storage_folder, f"{video_id}.npz")

    try:
        npz_data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        print(f"Error loading npz file: {e}")
        raise HTTPException(status_code=500, detail="Error loading video frames")
    return npz_data

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

def store_data(key: str, item: dict):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    value = json.dumps(dict(item))
    cursor.execute("REPLACE INTO key_value_store (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    return {"message": "Data stored successfully"}

def save_new_metadata(video_id, tracking_dict):
    try:
        metadata = retrieve_data(f"{video_id}_metadata")
        metadata.update(tracking_dict)
    except:
        metadata = tracking_dict
    store_data(f"{video_id}_metadata", metadata)

class Plugin():
    """
    Generic plugin class
    """

    def __init__(self, arguments={}, plugin_name="default"):
        self.plugin_name = plugin_name
        if arguments == {}:
            self.plugin = {}
            self.config = {}
            self.endpoints = {}
        else:
            self.plugin = arguments.plugin
            self.config = arguments.config
            self.endpoints = arguments.endpoints
            

        # Create a plugin-specific storage path
        self.plugin_storage_path = os.path.join(storage_folder, self.plugin_name)
        os.makedirs(self.plugin_storage_path, exist_ok=True)

    def plugin_info(self):
        """ int: The number of samples to take from the input video/images """
        return {"plugin": self.plugin,"config": self.config, "endpoints": self.endpoints}
    
    def get_config(self):
        return self.config
    
    def set_config(self, update: dict):
        self.config.update(update) # TODO: Validate config dict are all valid keys
        if "model_name" in update or "scheduler" in update or "loras" in update or "inverters" in update:
            self.set_model()
            # if response["status"] == "Failed":
            #     return response
        return self.config

    def progress_callback(self, progress, stage):
        if progress >= 0:
            print(f"{stage}: {progress*100}% complete")
        else:
            print(f"{stage}: Progress not available")


    def download_model(self, model_url, save_path, progress_callback=None):
        """Download a model with a progress bar and report progress in 5% increments."""
        resp = requests.get(model_url, stream=True)
        total_size = int(resp.headers.get('content-length', 0))
        downloaded_size = 0
        last_reported_progress = -0.05  # Initialize to -5% so the first callback happens at 0%

        with open(save_path, 'wb') as file:
            for data in resp.iter_content(chunk_size=1024):
                file.write(data)
                downloaded_size += len(data)
                progress = downloaded_size / total_size
                if progress >= last_reported_progress + 0.05:  # Check if we've advanced by another 5%
                    last_reported_progress = progress
                    if progress_callback:
                        progress_callback(progress, f"Downloading {os.path.basename(save_path)}")

        if progress_callback:
            progress_callback(1.0, f"Downloading {os.path.basename(save_path)} complete")

    def on_install(self, model_urls, progress_callback=None):
        """Install necessary models for the plugin and report detailed progress in 5% increments."""
        try:
            total_models = len(model_urls)
            current_model_index = 0

            for model_name, model_url in model_urls.items():
                model_path = os.path.join(self.plugin_storage_path, model_name)
                if not os.path.exists(model_path):
                    def model_progress_callback(local_progress, stage):
                        # Calculate the overall progress based on the current model index and local progress
                        overall_progress = ((current_model_index + local_progress) / total_models)
                        # Convert overall progress to percentage
                        progress_percentage = round(overall_progress * 100)
                        self.notify_main_system_of_installation_async(progress_percentage, stage)

                    print(f"Downloading {model_name}...")
                    self.download_model(model_url, model_path, model_progress_callback)
                else:
                    print(f"{model_name} already exists.")

                # After each model is processed (downloaded or skipped), increment the current_model_index
                current_model_index += 1
                # Notify for the completion of this model's installation
                self.notify_main_system_of_installation_async(round((current_model_index / total_models) * 100), f"{model_name} installation complete")

            # After all models are processed, notify completion
            self.notify_main_system_of_installation_async(100, "Installation complete")
        except Exception as e:
            self.notify_main_system_of_installation_async(-1, f"Installation failed: {str(e)}")
            print(f"Error installing resources for {self.plugin_name}: {str(e)}")

    def on_uninstall(self, progress_callback=None):
        """Clean up resources used by the plugin."""
        try:
            shutil.rmtree(self.plugin_storage_path)
            if progress_callback:
                progress_callback(1.0, "Uninstallation complete")
            print(f"Removed all resources for {self.plugin_name}.")
        except Exception as e:
            if progress_callback:
                progress_callback(-1, f"Uninstallation failed: {str(e)}")
            print(f"Error removing resources for {self.plugin_name}: {str(e)}")
    
    def notify_main_system_of_startup(self, status: str):
        callback_url = f"http://localhost:8000/plugin_callback/{self.plugin_name}/{status}"
        try:
            response = requests.post(callback_url)
            print("Response from main system:", response.json())  # Print the response content
            if response.json()["status"] == "success":
                print("Callback successful. Plugin is now in RUNNING state.")
            else:
                print("Callback failed. Check the main system.")
        except:
            print("Failed to notify the main system. Ensure it's running.")

    def notify_main_system_of_installation(self, progress, stage):
        # Ensure progress is rounded to the nearest whole number for reporting
        print(progress, stage)
        #progress_percentage = round(progress * 100)
        callback_url = f"http://localhost:8000/plugin_install_callback/{self.plugin_name}/{progress}/{stage.replace(' ', '%20')}"
        try:
            response = requests.post(callback_url)
            print(f"Installation progress update to main system: {progress}% complete. Current stage: {stage}")
        except Exception as e:
            print("Failed to notify the main system of installation progress:", e)

    def notify_main_system_of_uninstallation(self, progress, stage):
        callback_url = f"http://localhost:8000/plugin_uninstall_callback/{self.plugin_name}/{progress}/{stage}"
        try:
            response = requests.post(callback_url)
            print("Uninstallation progress update to main system:", response.json())
        except Exception as e:
            print("Failed to notify the main system of uninstallation progress:", e)
        
    def notify_main_system_of_installation_async(self, progress, stage):
        threading.Thread(target=self.notify_main_system_of_installation, args=(progress, stage)).start()


