from PySide6.QtWidgets import QApplication
import sys
from gui import ConfigGUI, PluginManagerGUI, Updater, ReportIssueDialog, LoginWidget
import argparse
from PySide6.QtGui import QScreen

parser = argparse.ArgumentParser()

parser.add_argument("-n", "--ui_name", help="Database name")
parser.add_argument("-p", "--plugin_name", help="Database name")


args = parser.parse_args()


def center_screen(screen):
    center = QScreen.availableGeometry(QApplication.primaryScreen()).center()
    geo = screen.frameGeometry()
    geo.moveCenter(center)
    screen.move(geo.topLeft())

ui_name = args.ui_name
plugin_name = args.plugin_name
app = QApplication(sys.argv)

if ui_name == "PluginManager":
    window = PluginManagerGUI()
elif ui_name == "Config":
    window = ConfigGUI(plugin_name)
elif ui_name == "Updater":
    window = Updater()
elif ui_name == "ReportIssueDialog":
    window = ReportIssueDialog()
elif ui_name == "Login":
    window = LoginWidget()
    
window.show()
center_screen(window)

try:
    sys.exit(app.exec())
except:
    pass

