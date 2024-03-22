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

if sys.platform == "win32":
    storage_folder = os.path.join(os.getenv('APPDATA'),"DeepMake")
elif sys.platform == "darwin":
    storage_folder = os.path.join(os.getenv('HOME'),"Library","Application Support","DeepMake")
elif sys.platform == "linux":
    storage_folder = os.path.join(os.getenv('HOME'),".local", "DeepMake")

if not os.path.exists(storage_folder):
    os.mkdir(storage_folder)

storage = SqliteStorage(name="storage", filename=os.path.join(storage_folder, 'huey_storage.db'))


def fetch_image(img_id):
    img_data = storage.peek_data(img_id)
    if img_data == huey.constants.EmptyData:
        # print("No image found for id", img_id)
        raise HTTPException(status_code=400, detail=f"No image found for id {img_id}")
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
    if not isinstance(img_data, bytes):
        raise HTTPException(status_code=400, detail=f"Data must be stored in bytes")
    storage.put_data(img_id, img_data)
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

class Plugin():
    """
    Generic plugin class
    """

    def __init__(self, arguments):
        self.plugin_name = "default"
        self.plugin = arguments.plugin
        self.config = arguments.config
        self.endpoints = arguments.endpoints

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
