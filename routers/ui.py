from fastapi import APIRouter
from PyQt6.QtWidgets import QApplication
import sys
from pyqt_gui_table import PluginManager
from qt_material import apply_stylesheet
import os
import subprocess

router = APIRouter()


@router.get("/ui/", tags=["ui"])
async def start_ui():
    return [{"username": "Rick"}, {"username": "Morty"}]

@router.get("/ui/plugin_manager", tags=["ui"])
async def plugin_manager():
    app = QApplication(sys.argv)
    window = PluginManager()
    apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")
    # window.setStyleSheet("QScrollBar::handle {background: #ffffff;} QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background: #ffffff;} QTableView {background-color: rgba(239,0,86,0.5); font-weight: bold;} QHeaderView::section {font-weight: bold; background-color: #7b3bff; color: #ffffff} QTableView::item:selected {background-color: #7b3bff; color: #ffffff;} QPushButton:pressed {color: #ffffff; background-color: #7b3bff;} QPushButton {color: #ffffff;}")
    window.show()
    try:
        sys.exit(app.exec())
    except:
        pass

@router.get("/ui/plugin_manager/install/{plugin_name}/{url}", tags=["ui"])
async def install_plugin(plugin_name: str, url: str):
    print("nice")
    folder_path = os.path.join(os.path.dirname(__file__), "plugin", plugin_name)
    if sys.platform != "win32":
        p = subprocess.Popen(f"git clone {url} {folder_path}".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen(f"git clone {url} {folder_path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if "already exists" in err.decode("utf-8"):
        print("Plugin already installed")
    else:
        print("Installed", plugin_name)
    return {"status": "success"}


@router.get("/ui/me", tags=["ui"])
async def read_user_me():
    return {"username": "fakecurrentuser"}


@router.get("/ui/{username}", tags=["ui"])
async def read_user(username: str):
    return {"username": username}