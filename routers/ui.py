from fastapi import APIRouter
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QScreen
import sys
import os
import subprocess
import requests
# from test import ConfigGUI

from gui import ConfigGUI, PluginManagerGUI, Updater

router = APIRouter()

@router.get("/ui/plugin_manager", tags=["ui"])
def plugin_manager():
    if sys.platform != "darwin":
        app = QApplication(sys.argv)
        window = PluginManagerGUI()
        window.show()
        center_screen(window)

        try:
            sys.exit(app.exec())
        except:
            pass
    else:
        subprocess.Popen("python mac_show_ui.py -n PluginManager".split())

@router.get("/ui/configure/{plugin_name}", tags=["ui"])
def plugin_config_ui(plugin_name: str):
    try:
        r = requests.get(f"http://127.0.0.1:8000/plugins/get_config/{plugin_name}")
        print(r.status_code)
        print(r.json())
    except:
        return {"status": "error", "message": "Please start the plugin first."}
    
    if sys.platform != "darwin":
        app = QApplication(sys.argv)
        window = ConfigGUI(plugin_name)
        window.show()
        center_screen(window)

        try:
            sys.exit(app.exec())
        except:
            pass
    else:
        subprocess.Popen(f"python mac_show_ui.py -n Config -p {plugin_name}".split())

@router.get("/ui/updater", tags=["ui"])
def update_gui():
    if sys.platform != "darwin":
        app = QApplication(sys.argv)
        window = Updater()
        window.show()
        center_screen(window)

        try:
            sys.exit(app.exec())
        except:
            pass
    else:
        subprocess.Popen("python mac_show_ui.py -n Updater".split())


def center_screen(screen):
    center = QScreen.availableGeometry(QApplication.primaryScreen()).center()
    geo = screen.frameGeometry()
    geo.moveCenter(center)
    screen.move(geo.topLeft())