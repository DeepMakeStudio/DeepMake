import os
import sys
import subprocess 
from fastapi import APIRouter
import requests
import io
from auth_handler import auth_handler as auth
import zipfile
from db_utils import retrieve_data 
from plugin import Plugin

router = APIRouter()

@router.post("/install/{plugin_name}")
async def install_plugin(plugin_name: str, plugin_dict: dict):
    url = plugin_dict[plugin_name]["url"]

    folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugin", plugin_name)
    plugin_folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugin")
    if ".git" in url:
        if sys.platform != "win32":
            p = subprocess.Popen(f"git clone {url} {folder_path}".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            p = subprocess.Popen(f"git clone {url} {folder_path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = p.communicate()
        print(out, err)
        if "already exists" in err.decode("utf-8"):
            print("Plugin already installed")
        else:
            print("Installed", plugin_name)
        # p = subprocess.Popen(f"unzip {plugin_name}.zip -d {plugin_folder_path}".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        r = requests.get(url)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(folder_path)
        # p = subprocess.Popen(f"tar -xf {plugin_name}.zip -C {plugin_folder_path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    Plugin().on_install({})
    
    return {"status": "success"}

@router.get("/uninstall/{plugin_name}")
async def uninstall_plugin(plugin_name: str):
    folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugin", plugin_name)
    print(folder_path)
    if sys.platform != "win32":
        p = subprocess.Popen(f"rm -rf {folder_path}".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen(f"rmdir /s /q {folder_path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    Plugin().on_uninstall()
    return {"status": "success"}

@router.get("/update/{plugin_name}/{version}")
def update_plugin(plugin_name: str, version: str):
    if plugin_name != "DeepMake":
        plugin_dict = plugin_info()

        plugin_url = plugin_dict[plugin_name]["url"]
        folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugin", plugin_name)

    if plugin_name == "DeepMake" or ".git" in plugin_url:
        origin_folder = os.path.dirname(os.path.dirname(__file__))
        if plugin_name != "DeepMake":
            os.chdir(os.path.join(origin_folder, "plugin", plugin_name))
            # print(p.communicate())
        print(f"git checkout {version}", os.getcwd()
        if sys.platform != "win32":
            p = subprocess.Popen(f"git checkout {version} ".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            p = subprocess.Popen(f"git checkout {version} ", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        os.chdir(origin_folder)
    else:
        zip_name = plugin_url.split("/")[-1].split("-")[0]
        new_version_url = "/".join(plugin_url.split("/")[:-1]) + "/" + f"{zip_name}-{version}.zip"
        print(new_version_url)
        r = requests.get(new_version_url)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(folder_path)

    return {"status": "success", "version": f"{version}"}

@router.get("/get_plugin_info")
def plugin_info():
    print(auth.logged_in)
    try:
        plugin_dict = auth.get_url("https://deepmake.com/plugins.json")
    except:
        print("Error retrieving plugin info, using cached version")
        plugin_dict = retrieve_data("plugin_info")
    return plugin_dict