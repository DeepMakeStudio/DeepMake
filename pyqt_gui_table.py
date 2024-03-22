from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QProgressBar, QComboBox, QHBoxLayout, QListWidget, QHeaderView, QTableWidget, QVBoxLayout, QTableWidgetItem, QDialog, QScrollArea, QDialogButtonBox
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from qt_material import apply_stylesheet
import os
import json
import subprocess
fastapi_launcher_path = os.path.join(os.path.dirname(__file__), "plugin")
import sys
import requests

client = requests.Session()
 
class Worker(QObject):
    popen_string = " "
    finished = pyqtSignal()
    # progress = pyqtSignal(int)
    def run(self):
        """Long-running task."""
        if sys.platform != "win32":
            p = subprocess.Popen(self.popen_string.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:   
            p = subprocess.Popen(self.popen_string, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()

        self.finished.emit()

class PluginManager(QWidget):
    def __init__(self):
        super().__init__() 
        self.title = "Plugin Manager"
        self.left = 0
        self.top = 0
        self.width = 1000
        self.height = 300
        self.setWindowTitle(self.title) 
        self.setGeometry(self.left, self.top, self.width, self.height) 
        # self.setStyleSheet( "color: white; border-color: #7b3bff")
        r = client.get(f"http://127.0.0.1:8000/plugins/get_config/Diffusers")
   
        
        with open(os.path.join(os.path.dirname(__file__), "gui_info.json")) as f:
            self.plugin_dict = json.load(f)
        self.createTable() 

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.tableWidget)
        # compute the correct minimum width
        width = (self.tableWidget.sizeHint().width() + 
            self.scrollArea.verticalScrollBar().sizeHint().width() + 
            self.scrollArea.frameWidth() * 2)
        self.scrollArea.setMinimumWidth(width)

        self.layout = QVBoxLayout() 
        self.layout.addWidget(self.tableWidget) 
        self.setLayout(self.layout) 
        # self.setFixedSize(self.layout.sizeHint())


    def createTable(self): 
        self.tableWidget = QTableWidget() 
        row_count = len(self.plugin_dict["plugin"])
        column_count = 5

        self.tableWidget.setRowCount(row_count)  
        self.tableWidget.setColumnCount(column_count) 
        self.button_dict = {}  

        for row in range(row_count):
            plugin_name = list(self.plugin_dict["plugin"].keys())[row]
            for col in range(column_count):
                if col == 0:
                    self.tableWidget.setItem(row, col, QTableWidgetItem(plugin_name))
                elif col == 1:
                    self.tableWidget.setItem(row, col, QTableWidgetItem(self.plugin_dict["plugin"][plugin_name]["Description"]))
                elif col == 2:
                    item = QTableWidgetItem(self.plugin_dict["plugin"][plugin_name]["Version"])
                    self.tableWidget.setItem(row, col, item)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
                elif col == 3:
                    if plugin_name in os.listdir(fastapi_launcher_path):
                        self.Installed(plugin_name)
                    else:     
                        self.install_button_creation(plugin_name)
                elif col == 4:
                    if plugin_name in os.listdir(fastapi_launcher_path):
                        button = QPushButton(f"Manage")
                        button.clicked.connect(lambda _, name = plugin_name: self.uninstall_plugin(name))
                        self.button_dict[plugin_name] = button
                        self.tableWidget.setCellWidget(row, col, button)                    
                    else:
                        self.manage(plugin_name)
                        


        self.tableWidget.setShowGrid(False)
        self.tableWidget.setHorizontalHeaderLabels(['Name', 'Description', 'Version', 'Install', "Manage"])
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)   
        self.tableWidget.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

    def install_button_creation(self, plugin_name):
        row = list(self.plugin_dict['plugin'].keys()).index(plugin_name)
        button = QPushButton(f"Install")
        button.clicked.connect(lambda _, name = plugin_name: self.install_plugin(name))
        self.button_dict[plugin_name] = button
        self.tableWidget.setItem(row, 3, QTableWidgetItem(" "))
        self.tableWidget.setCellWidget(row, 3, button)

    def install_plugin(self, plugin_name):
        if plugin_name in os.listdir(fastapi_launcher_path):
            print("Plugin already installed")
            return
    
        row_number = list(self.plugin_dict['plugin'].keys()).index(plugin_name)
        # installing_button = QPushButton(f"Installing")
        self.tableWidget.removeCellWidget(row_number, 3)

        installing_item = QTableWidgetItem("Installing...")
        self.tableWidget.setItem(row_number, 3, installing_item)
        installing_item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        clone_link = self.plugin_dict["plugin"][plugin_name]["url"] + ".git"
        folder_path = os.path.join(os.path.dirname(__file__), "plugin", plugin_name)
        print("Installing", plugin_name)
        r = client.get(f"http://127.0.0.1:8000/")
        print(r.text)

        self.thread_process(f"conda env create -f {folder_path}/environment.yml", row_number)

    def uninstall_plugin(self, plugin_name):
        if plugin_name not in os.listdir(fastapi_launcher_path):
            print("Plugin not installed")
            return
        
        dlg = CustomDialog(plugin_name)
        if dlg.exec():
            print("Uninstalling", plugin_name)
            folder_path = os.path.join(os.path.dirname(__file__), "plugin", plugin_name)
            if sys.platform != "win32":
                p = subprocess.Popen(f"rm -rf {folder_path}".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            else:
                p = subprocess.Popen(f"rm -rf {folder_path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.button_dict.pop(plugin_name)
            self.tableWidget.removeCellWidget(list(self.plugin_dict['plugin'].keys()).index(plugin_name), 2)
            self.install_button_creation(plugin_name)
            self.manage(plugin_name)
    
    def manage(self, plugin_name):
        row = list(self.plugin_dict['plugin'].keys()).index(plugin_name)
        item = QTableWidgetItem("Install First!")
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.tableWidget.removeCellWidget(row, 4)
        self.tableWidget.setItem(row, 4, item)

    
    def uninstall_button_creation(self, plugin_name):
        row = list(self.plugin_dict['plugin'].keys()).index(plugin_name)
        button = QPushButton(f"Manage")
        button.clicked.connect(lambda _, name = plugin_name: self.uninstall_plugin(name))
        self.button_dict[plugin_name] = button
        self.tableWidget.setItem(row, 4, QTableWidgetItem(" "))
        self.tableWidget.setCellWidget(row, 4, button)
        print("Finish env", plugin_name)    

    def thread_process(self, popen_string, row_number):

        self.thread = QThread()

        self.worker = Worker()
        self.worker.popen_string = popen_string

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
        plugin_name = list(self.plugin_dict["plugin"].keys())[row_number]
        self.thread.finished.connect(lambda: self.uninstall_button_creation(plugin_name))
        self.thread.finished.connect(lambda: self.Installed(plugin_name))
    
    def Installed(self, plugin_name):
        row = list(self.plugin_dict['plugin'].keys()).index(plugin_name)
        install_label = QTableWidgetItem("Installed")
        install_label.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.tableWidget.setItem(row, 3, install_label)


class CustomDialog(QDialog):
    def __init__(self, plugin_name):
        super().__init__()
        self.name = plugin_name
        self.setWindowTitle("Manage")
        self.setGeometry(0, 0, 500, 200) 


        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton("Uninstall", QDialogButtonBox.ButtonRole.AcceptRole)
        # self.buttonBox.addButton("Update to Latest", QDialogButtonBox.ButtonRole.RejectRole)
        self.buttonBox.accepted.connect(self.accept)
        # self.buttonBox.centerButtons()
        # uninstall_button = QPushButton()
        # uninstall_button.addButton("Uninstall", QDialogButtonBox.ButtonRole.AcceptRole) 
        self.layout = QVBoxLayout()
        self.createTable()
        self.update_button = QPushButton("Update to Latest")
        self.update_button.clicked.connect(lambda: self.update_plugin(self.name))
        # self.test_button = QPushButton("Test")
        self.tableWidget.setCellWidget(1,0, self.buttonBox)
        self.tableWidget.setCellWidget(1, 2, self.update_button)
        # self.tableWidget.setCellWidget(1, 1,self.test_button) 
        # self.test_button.clicked.connect(self.test_plugin)
        # message = QLabel("Do you want to uninstall?")
        # self.layout.addWidget(message)
        self.layout.addWidget(self.tableWidget)
        # self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def test_plugin(self):
        self.tableWidget.setItem(0, 1, QTableWidgetItem("Testing..."))


    def update_plugin(self, plugin_name):
        if len(self.tag_list) == 0:
            print("No versioning")
            return
        version = self.update_button.text().split()[-1]
        if version == "Latest":
            version = self.tag_list[0]
        print("Updating", plugin_name, "to version", version)

        origin_folder = os.path.dirname(__file__)
        os.chdir(os.path.join(origin_folder, "plugin", plugin_name))
        p = subprocess.Popen(f"git checkout {version} ".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        # print(p.communicate())
        os.chdir(origin_folder)
        # current_tag = self.getVersion()
        self.tableWidget.setItem(0, 0, QTableWidgetItem(f"Current Version: {version}"))
        print("Updated", plugin_name, "to version", version)

    def version_management(self):
        tag_list = []
        origin_folder = os.path.dirname(__file__)
        os.chdir(os.path.join(origin_folder, "plugin", self.name))
        tags = subprocess.check_output("git tag".split()).decode("utf-8")
        os.chdir(origin_folder)
        for label in tags.split("\n")[:-1]:
            tag_list.append(label)
        return tag_list

    def createTable(self): 
        self.tableWidget = QTableWidget() 
        row_count = 2
        column_count = 3

        self.tableWidget.setRowCount(row_count)  
        self.tableWidget.setColumnCount(column_count) 
        self.button_dict = {}  
        current_tag = self.getVersion()
        self.tableWidget.setItem(0, 0, QTableWidgetItem(f"Current Version: {current_tag}"))
        self.tableWidget.setItem(0, 1, QTableWidgetItem("Available Versions"))
        dropdown = QComboBox()
        self.tag_list = self.version_management()
        self.tag_list.reverse()
        dropdown.addItems(self.tag_list)
        dropdown.currentTextChanged.connect(self.changeVersion)

        self.tableWidget.setCellWidget(0, 2, dropdown)

        self.tableWidget.setShowGrid(False)
        self.tableWidget.horizontalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setVisible(False)
        # self.tableWidget.setHorizontalHeaderLabels(['Name', 'Description', 'Version', 'Install'])

        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    def changeVersion(self, text):
        self.update_button.setText(f"Update to {text}")

    def getVersion(self):
        origin_folder = os.path.join(fastapi_launcher_path, self.name)
        os.chdir(origin_folder)
        try:
            tag = subprocess.check_output("git describe --tags".split()).decode("utf-8").split("\n")[0]
        except:
            tag = "0.0.0"
        os.chdir(os.path.dirname(__file__))
        # print(tag)
        return tag

# app = QApplication(sys.argv)

# window = Window()

# apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")

# window.setStyleSheet("QScrollBar::handle {background: #ffffff;} QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background: #ffffff;} QTableView {background-color: rgba(239,0,86,0.5); font-weight: bold;} QHeaderView::section {font-weight: bold; background-color: #7b3bff; color: #ffffff} QTableView::item:selected {background-color: #7b3bff; color: #ffffff;} QPushButton:pressed {color: #ffffff; background-color: #7b3bff;} QPushButton {color: #ffffff;}")

# window.show()

# sys.exit(app.exec())
