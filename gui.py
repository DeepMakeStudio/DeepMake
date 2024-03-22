from PyQt6.QtWidgets import QWidget, QPushButton, QLineEdit, QComboBox, QSlider, QSizePolicy, QHBoxLayout, QVBoxLayout, QCheckBox, QDialog, QScrollArea, QDialogButtonBox, QLabel, QFileDialog, QTableWidget, QHeaderView, QTableWidgetItem, QApplication, QProgressBar, QComboBox, QHBoxLayout, QListWidget, QHeaderView, QTableWidget, QVBoxLayout, QTableWidgetItem, QDialog, QScrollArea, QDialogButtonBox, QSlider, QSizePolicy, QCheckBox, QLabel, QLineEdit, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
import os
fastapi_launcher_path = os.path.join(os.path.dirname(__file__), "plugin")
import sys
import requests
import subprocess
import json 
import webbrowser

client = requests.Session()

class setWorker(QObject):
    name = ""
    output_config = {}
    finished = pyqtSignal()
    # progress = pyqtSignal(int)
    def run(self):
        """Long-running task."""
        r = client.put(f"http://127.0.0.1:8000/plugins/set_config/{self.name}", json = self.output_config)

        self.finished.emit()   





class ConfigGUI(QWidget):
    def __init__(self, plugin_name):
        super().__init__() 
        self.name = plugin_name
        self.title = f"{plugin_name} Configuration"
        self.left = 0
        self.top = 0
        self.width = 800
        self.height = 300
        self.setWindowTitle(self.title) 
        self.setGeometry(self.left, self.top, self.width, self.height)    

        r = client.get(f"http://127.0.0.1:8000/plugins/get_config/{plugin_name}")
        config = r.json()
        self.output_config = config
        self.layout = QVBoxLayout() 
        self.widget_dict = {}


        self.guiFromConfig(config)
       

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.start)
        self.layout.addWidget(self.submit_button) 
        self.setLayout(self.layout) 
        # self.setFixedSize(self.layout.sizeHint())


    def guiFromConfig(self, config):
        for key in config:
            value = config[key]
            print(type(value))  
            label = QLabel(key)
            self.layout.addWidget(label)
            
            if isinstance(value, list):
                dropdown = QComboBox()
                for item in value:
                    dropdown.addItem(item)
                dropdown.setEditable(True)
                dropdown.currentTextChanged.connect(lambda text, key = key: self.editConfig(key, text))
                self.layout.addWidget(dropdown)
            elif isinstance(value, bool):
                checkbox = QCheckBox(f"{key}")
                checkbox.stateChanged.connect(lambda state, key = key: self.setBool(key, state))
                self.layout.addWidget(checkbox)
            elif isinstance(value, int):
                print(key, value)
                h_layout = QHBoxLayout()
                number_label = QLabel(f"{value}")

                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setMinimum(1)
                slider.setMaximum(10000)
                slider.setValue(value)
                slider.valueChanged.connect(lambda number, key = key: self.editConfig(key, number))
                slider.valueChanged.connect(lambda number, label= number_label: self.changeValue(label, number))
                policy = slider.sizePolicy()
                policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
                slider.setSizePolicy(policy)
                h_layout.addWidget(slider)
                h_layout.addWidget(number_label)
                self.layout.addLayout(h_layout)
            elif value == "Image":
                h_layout = QHBoxLayout()
                file_button = QPushButton("Choose File")
                image_label = QLabel("No File Chosen")
                
                file_button.clicked.connect(lambda: self.openFileNameDialog(image_label))
                h_layout.addWidget(image_label)
                h_layout.addWidget(file_button)
                self.layout.addLayout(h_layout)
            elif value == "Point":
                h_layout = QHBoxLayout()
                x_label = QLabel("X")
                x_box = QLineEdit("0")
                y_label = QLabel("Y")
                y_box = QLineEdit("1")
                x_box.textChanged.connect(lambda text, key = key: self.editConfigNumberList(key, [text, y_box.text()], float))
                y_box.textChanged.connect(lambda text, key = key: self.editConfigNumberList(key, [x_box.text(), text], float))
                h_layout.addWidget(x_label)
                h_layout.addWidget(x_box)
                h_layout.addWidget(y_label)
                h_layout.addWidget(y_box)
                self.layout.addLayout(h_layout)
            elif value == "Box":
                h_layout = QHBoxLayout()
                x_label = QLabel("X")
                x_box = QLineEdit("0")
                y_label = QLabel("Y")
                y_box = QLineEdit("1")
                w_label = QLabel("X")
                w_box = QLineEdit("0")
                h_label = QLabel("Y")
                h_box = QLineEdit("1")
                x_box.textChanged.connect(lambda text, key = key: self.editConfigNumberList(key, [text, y_box.text(), w_box.text(), h_box.text()], float))
                y_box.textChanged.connect(lambda text, key = key: self.editConfigNumberList(key, [x_box.text(), text, w_box.text(), h_box.text()], float))
                w_box.textChanged.connect(lambda text, key = key: self.editConfigNumberList(key, [x_box.text(), y_box.text(), text, h_box.text()], float))
                h_box.textChanged.connect(lambda text, key = key: self.editConfigNumberList(key, [x_box.text(), y_box.text(), w_box.text(), text], float))
                h_layout.addWidget(x_label)
                h_layout.addWidget(x_box)
                h_layout.addWidget(y_label)
                h_layout.addWidget(y_box)
                h_layout.addWidget(w_label)
                h_layout.addWidget(w_box)
                h_layout.addWidget(h_label)
                h_layout.addWidget(h_box)
                self.layout.addLayout(h_layout)
            elif isinstance(value, str):
                # self.widget_dict[key] = QLineEdit(f"{value}")
                text_box = QLineEdit(f"{value}")
                # text_box.textChanged.connect(lambda key = key, text=text_box.text(): self.editConfig(key, text))
                text_box.textChanged.connect(lambda text, key = key: self.editConfig(key, text))
                # self.widget_dict[key] = text_box
                self.layout.addWidget(text_box) 


    def openFileNameDialog(self, image_label):
        fname = QFileDialog.getOpenFileName(self, 'Open file', 
         'c:\\',"Image files (*.jpg *.png)")
        # image_label.setPixmap(QPixmap(fname))
        image_label.setText(fname[0])
        self.editConfig("image", fname[0])
    
    def editConfigNumberList(self, key, num_list, func):
        list_to_send = []
        try: 
            for num in num_list:
                num_form = func(num)
                if num_form < 0:
                    num_form = 0.0
                elif num_form > 1:
                    num_form = 1.0
                list_to_send.append(num_form)
            self.output_config[key] = list_to_send
            print(self.output_config)
        except:
            print("One or more inputs invalid")
            

    def changeValue(self, label, value):
        label.setText(f"{value}")
    def editConfig(self, key, text):
        self.output_config[key] = text
        print(self.output_config)
    def setBool(self, key, state):
        if state == 2:
            self.output_config[key] = True
        else:
            self.output_config[key] = False
        print(self.output_config)
    
    def thread_process(self):

        self.thread = QThread()

        self.worker = setWorker()
        self.worker.name = self.name
        self.worker.output_config = self.output_config

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.thread.finished.connect(self.renable)
    
    def renable(self):
        self.submit_button.setEnabled(True)
        self.submit_button.setText("Submit")
    
    def start(self):
        self.submit_button.setEnabled(False)
        self.submit_button.setText("Submitting...")
        self.thread_process()

# class FileExplorer(QWidget):

#     def __init__(self):
#         super().__init__()
#         self.title = 'File Explorer'
#         self.left = 10
#         self.top = 10
#         self.width = 640
#         self.height = 480
#         self.initUI()

#     def initUI(self):
#         self.setWindowTitle(self.title)
#         self.setGeometry(self.left, self.top, self.width, self.height)
#         # self.openFileNameDialog()
#         self.show()

    # def openFileNameDialog(self):
    #     # options = QFileDialog.options()
    #     options = QFileDialog.DontUseNativeDialog
    #     fileName, _ = QFileDialog.getOpenFileName(self,"Choose File", "","csv (*.csv)", 
    #     options=options)
    #     df=pd.read_csv(fileName)
    #     df.plot()
    #     plt.show()

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
class PluginManagerGUI(QWidget):
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
        r = client.get(f"http://127.0.0.1:8000/plugins/get_list")
   
        
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
                        if "url" in self.plugin_dict["plugin"][plugin_name].keys():

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
        if "url" not in self.plugin_dict["plugin"][plugin_name].keys():
            button = QPushButton(f"Subscribe")
            button.clicked.connect(lambda: webbrowser.open("https://deepmake.com"))
        else:
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
        r = client.get(f"http://127.0.0.1:8000/ui/plugin_manager/install/{plugin_name}", json = self.plugin_dict)

        self.thread_process(f"conda env create -f {folder_path}/environment.yml", row_number)

    def uninstall_plugin(self, plugin_name):
        if plugin_name not in os.listdir(fastapi_launcher_path):
            print("Plugin not installed")
            return
        
        dlg = CustomDialog(plugin_name)
        if dlg.exec():
            print("Uninstalling", plugin_name)
            r = client.get(f"http://127.0.0.1:8000/ui/plugin_manager/uninstall/{plugin_name}")
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

    def update_plugin(self, plugin_name):
        if len(self.tag_list) == 0:
            print("No versioning")
            return
        version = self.update_button.text().split()[-1]
        if version == "Latest":
            version = self.tag_list[0]
        r = client.get(f"http://127.0.0.1:8000/ui/plugin_manager/update/{plugin_name}/{version}")
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

class Updater(QWidget):
    def __init__(self):
        super().__init__()
        # self.name = plugin_name
        self.setWindowTitle("Update")
        self.setGeometry(0, 0, 500, 200) 


        # self.button = QPushButton("Uninstall")
        # self.buttonBox.addButton("Uninstall", QDialogButtonBox.ButtonRole.AcceptRole)
        # self.buttonBox.addButton("Update to Latest", QDialogButtonBox.ButtonRole.RejectRole)
        # self.buttonBox.accepted.connect(self.accept)
        # self.buttonBox.centerButtons()
        # uninstall_button = QPushButton()
        # uninstall_button.addButton("Uninstall", QDialogButtonBox.ButtonRole.AcceptRole) 
        self.layout = QVBoxLayout()
        self.createTable()
        self.update_button = QPushButton("Update to Latest")
        self.update_button.clicked.connect(self.update_plugin)
        # self.test_button = QPushButton("Test")
        # self.tableWidget.setCellWidget(1,0, self.buttonBox)
        # self.tableWidget.setCellWidget(1, 2, self.update_button)
        # self.tableWidget.setCellWidget(1, 1,self.test_button) 
        # self.test_button.clicked.connect(self.test_plugin)
        # message = QLabel("Do you want to uninstall?")
        # self.layout.addWidget(message)
        self.layout.addWidget(self.tableWidget)
        self.layout.addWidget(self.update_button)
        # self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def test_plugin(self):
        self.tableWidget.setItem(0, 1, QTableWidgetItem("Testing..."))


    def update_plugin(self):
        if len(self.tag_list) == 0:
            print("No versioning")
            return
        version = self.update_button.text().split()[-1]
        if version == "Latest":
            version = self.tag_list[0]
        print("Updating to version", version)

        r = client.get(f"http://127.0.0.1:8000/ui/plugin_manager/update/DeepMake/{version}")
        # print(p.communicate())
        # current_tag = self.getVersion()
        self.tableWidget.setItem(0, 0, QTableWidgetItem(f"Current Version: {version}"))
        print("Updated to version", version)

    def version_management(self):
        tag_list = []
        tags = subprocess.check_output("git tag".split()).decode("utf-8")
        for label in tags.split("\n")[:-1]:
            tag_list.append(label)
        print(tag_list)
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
        try:
            tag = subprocess.check_output("git describe --tags".split()).decode("utf-8").split("\n")[0]
        except:
            tag = "0.0.0"
        print(tag)
        # print(tag)
        return tag