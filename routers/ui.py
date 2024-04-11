from fastapi import APIRouter
from PySide6.QtWidgets import QApplication
import sys
from qt_material import apply_stylesheet
import os
import subprocess
# from test import ConfigGUI

from gui import ConfigGUI, PluginManagerGUI, Updater

router = APIRouter()


@router.get("/ui/plugin_manager", tags=["ui"])
def plugin_manager():
    app = QApplication(sys.argv)
    window = PluginManagerGUI()
    apply_stylesheet(app, theme='dark_purple.xml')
    window.show()
    try:
        sys.exit(app.exec())
    except:
        pass

@router.get("/ui/configure/{plugin_name}", tags=["ui"])
def plugin_config_ui(plugin_name: str):
    app = QApplication(sys.argv)
    window = ConfigGUI(plugin_name)
    apply_stylesheet(app, theme='dark_purple.xml')
    window.show()
    try:
        sys.exit(app.exec())
    except:
        pass

@router.get("/ui/plugin_manager/install/{plugin_name}", tags=["ui"])
async def install_plugin(plugin_name: str, plugin_dict: dict):
    url = plugin_dict["plugin"][plugin_name]["url"] + ".git"
    folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugin", plugin_name)
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
    return {"status": "success"}

@router.get("/ui/plugin_manager/uninstall/{plugin_name}", tags=["ui"])
async def uninstall_plugin(plugin_name: str):
    folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugin", plugin_name)
    print(folder_path)
    if sys.platform != "win32":
        p = subprocess.Popen(f"rm -rf {folder_path}".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen(f"rm -rf {folder_path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"status": "success"}

@router.get("/ui/plugin_manager/update/{plugin_name}/{version}", tags=["ui"])
def update_plugin(plugin_name: str, version: str):


    origin_folder = os.path.dirname(os.path.dirname(__file__))
    if plugin_name != "DeepMake":
        os.chdir(os.path.join(origin_folder, "plugin", plugin_name))
        # print(p.communicate())
    p = subprocess.Popen(f"git checkout {version} ".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    os.chdir(origin_folder)

    return {"status": "success"}


@router.get("/ui/updater", tags=["ui"])
def update_gui():
    app = QApplication(sys.argv)
    window = Updater()
    apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")
    window.show()
    try:
        sys.exit(app.exec())
    except:
        pass

