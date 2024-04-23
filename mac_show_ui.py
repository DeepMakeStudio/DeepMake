from PySide6.QtWidgets import QApplication
import sys
from gui import PluginManagerGUI, ConfigGUI, Updater
import argparse
parser = argparse.ArgumentParser()

parser.add_argument("-n", "--ui_name", help="Database name")
parser.add_argument("-p", "--plugin_name", help="Database name")


args = parser.parse_args()

ui_name = args.ui_name
plugin_name = args.plugin_name
app = QApplication(sys.argv)

if ui_name == "PluginManager":
    window = PluginManagerGUI()
elif ui_name == "Config":
    window = ConfigGUI(plugin_name)
elif ui_name == "Updater":
    window = Updater()
    
window.show()
# center_screen(window)

try:
    sys.exit(app.exec())
except:
    pass