from fastapi import APIRouter
from PyQt6.QtWidgets import QApplication
from qt_material import apply_stylesheet
from config_gui import ConfigGUI
import sys

router = APIRouter()
@router.get("/ui/configure/{plugin_name}", tags=["ui"])
def plugin_config_ui(plugin_name: str):
    app = QApplication(sys.argv)
    window = ConfigGUI(plugin_name)
    apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")
    window.show()
    try:
        sys.exit(app.exec())
    except:
        pass