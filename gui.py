from PySide6.QtWidgets import QWidget, QPushButton, QLineEdit, QTextEdit, QComboBox, QSlider, QSizePolicy, QHBoxLayout, QVBoxLayout, QCheckBox, QDialog, QScrollArea, QDialogButtonBox, QLabel, QFileDialog, QTableWidget, QHeaderView, QTableWidgetItem, QApplication, QProgressBar, QComboBox, QHBoxLayout, QListWidget, QHeaderView, QTableWidget, QVBoxLayout, QTableWidgetItem, QDialog, QScrollArea, QDialogButtonBox, QSlider, QSizePolicy, QCheckBox, QLabel, QLineEdit, QFileDialog
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QIcon, QPixmap
import os
fastapi_launcher_path = os.path.join(os.path.dirname(__file__), "plugin")
import sys
import requests
import subprocess
import webbrowser

client = requests.Session()



class setWorker(QObject):
    name = ""
    output_config = {}
    finished = Signal()
    # progress = Signal(int)
    def run(self):
        """Long-running task."""
        r = client.put(f"http://127.0.0.1:8000/plugins/set_config/{self.name}", json = self.output_config)

        self.finished.emit()   


class ConfigGUI(QWidget):
    def __init__(self, plugin_name):
        super().__init__() 
        self.name = plugin_name
        self.title = f"{plugin_name} Configuration"
        self.left = 100
        self.top = 100
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
    plugin_name = ""
    finished = Signal()
    plugin_dict = {}
    # progress = Signal(int)
    def run(self):
        """Long-running task."""
        r = client.post(f"http://127.0.0.1:8000/plugin_manager/install/{self.plugin_name}", json = self.plugin_dict)

        
        self.finished.emit()

class UninstallWorker(QObject):
    plugin_name = ""
    finished = Signal()
    def run(self):
        r = client.get(f"http://127.0.0.1:8000/plugin_manager/uninstall/{self.plugin_name}")

        self.finished.emit()
    

class PluginManagerGUI(QWidget):
    def __init__(self):
        super().__init__() 
        
        self.title = "Plugin Manager"
        self.left = 0
        self.top = 0
        self.width = 1300
        self.height = 300
        self.setWindowTitle(self.title) 
        self.setGeometry(100, 100, self.width, self.height) 
        # self.setStyleSheet( "color: white; border-color: #7b3bff")

        
        self.plugin_dict = requests.get("http://127.0.0.1:8000/plugin_manager/get_plugin_info").json()

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
        self.threads = [QThread() for i in range(len(self.plugin_dict.keys()))]
        self.workers = [Worker() for i in range(len(self.plugin_dict.keys()))]
    
        


        # self.setFixedSize(self.layout.sizeHint())


    def createTable(self): 
        self.tableWidget = QTableWidget() 
        row_count = len(self.plugin_dict.keys())
        column_count = 5

        self.tableWidget.setRowCount(row_count)  
        self.tableWidget.setColumnCount(column_count) 
        self.button_dict = {}  

        for row in range(row_count):
            plugin_name = list(self.plugin_dict.keys())[row]
            for col in range(column_count):
                if col == 0:
                    plugin_name_item = QTableWidgetItem(plugin_name)
                    plugin_name_item.setFlags(Qt.ItemIsEnabled)
                    self.tableWidget.setItem(row, col, plugin_name_item)
                elif col == 1:
                    description_item = QTableWidgetItem(self.plugin_dict[plugin_name]["Description"])
                    description_item.setFlags(Qt.ItemIsEnabled)
                    self.tableWidget.setItem(row, col, description_item)
                elif col == 2:
                    if "Version" not in self.plugin_dict[plugin_name].keys():
                        item = QTableWidgetItem("0.0.0")
                    else:
                        item = QTableWidgetItem(self.plugin_dict[plugin_name]["Version"])
                    item.setFlags(Qt.ItemIsEnabled)
                    self.tableWidget.setItem(row, col, item)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
                elif col == 3:
                    if plugin_name in os.listdir(fastapi_launcher_path):
                        self.Installed(plugin_name)
                    else:     
                        self.install_button_creation(plugin_name)
                elif col == 4:
                    if plugin_name in os.listdir(fastapi_launcher_path):
                        if "url" in self.plugin_dict[plugin_name].keys():

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
        
        row = list(self.plugin_dict.keys()).index(plugin_name)
        if "url" not in self.plugin_dict[plugin_name].keys():
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
    
        row_number = list(self.plugin_dict.keys()).index(plugin_name)
        # installing_button = QPushButton(f"Installing")
        self.tableWidget.removeCellWidget(row_number, 3)

        installing_item = QTableWidgetItem("Installing...")
        installing_item.setFlags(Qt.ItemIsEnabled)
        self.tableWidget.setItem(row_number, 3, installing_item)
        installing_item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        folder_path = os.path.join(os.path.dirname(__file__), "plugin", plugin_name)
        # if row_number == 0:
        #     thread = self.thread0
        # elif row_number == 1:
        #     thread = self.thread1
        # elif row_number == 2:
        #     thread = self.thread2
        # elif row_number == 3:
        #     thread = self.thread3
        thread = ""
        self.thread_process(f"conda env create -f {folder_path}/environment.yml", row_number, thread)

    def uninstall_plugin(self, plugin_name):
        if plugin_name not in os.listdir(fastapi_launcher_path):
            print("Plugin not installed")
            return
        dlg = CustomDialog(plugin_name, self.plugin_dict[plugin_name])
        if dlg.exec():
            print("Uninstalling", plugin_name)
            self.thread_uninstall(plugin_name)
            # self.button_dict.pop(plugin_name)
            # self.tableWidget.removeCellWidget(list(self.plugin_dict.keys()).index(plugin_name), 2)
            self.install_button_creation(plugin_name)
            self.manage(plugin_name)
    def changeVersion(self, text):
        self.tableWidget.setCellWidget(1, 2, text)

    def thread_uninstall(self, plugin_name):
        self.uninstall_worker = UninstallWorker()
        self.uninstall_thread = QThread()
        self.uninstall_worker.plugin_name = plugin_name

        self.uninstall_worker.moveToThread(self.uninstall_thread)
        self.uninstall_thread.started.connect(self.uninstall_worker.run)
        self.uninstall_worker.finished.connect(self.uninstall_thread.quit)
        self.uninstall_worker.finished.connect(self.uninstall_worker.deleteLater)
        self.uninstall_thread.finished.connect(self.uninstall_thread.deleteLater)

        self.uninstall_thread.start()
        self.uninstall_thread.finished.connect(lambda: self.button_dict.pop(plugin_name))
        self.uninstall_thread.finished.connect(lambda: self.tableWidget.removeCellWidget(list(self.plugin_dict.keys()).index(plugin_name), 4))
        self.uninstall_thread.finished.connect(lambda: self.install_button_creation(plugin_name))
        self.uninstall_thread.finished.connect(lambda: self.manage(plugin_name))

    
    def manage(self, plugin_name):
        row = list(self.plugin_dict.keys()).index(plugin_name)
        item = QTableWidgetItem("Install First!")
        item.setFlags(Qt.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.tableWidget.removeCellWidget(row, 4)
        self.tableWidget.setItem(row, 4, item)

    
    def uninstall_button_creation(self, plugin_name):
        row = list(self.plugin_dict.keys()).index(plugin_name)
        button = QPushButton(f"Manage")
        button.clicked.connect(lambda _, name = plugin_name: self.uninstall_plugin(name))
        self.button_dict[plugin_name] = button
        self.tableWidget.setItem(row, 4, QTableWidgetItem(" "))
        self.tableWidget.setCellWidget(row, 4, button)
        print("Finish env", plugin_name)    

    def thread_process(self, popen_string, row_number, thread):

        plugin_name = list(self.plugin_dict.keys())[row_number]
        # while not self.thread.isFinished():
        #     time.sleep(3)
        #     wait_label = QTableWidgetItem(f"Waiting...")
        #     self.tableWidget.removeCellWidget(row_number, 3)
        #     self.tableWidget.setItem(row_number, 3, wait_label)
        #     print("Waiting for thread to finish")
        # self.thread = QThread()
        worker = self.workers[row_number]
        thread = self.threads[row_number]

        worker.popen_string = popen_string
        worker.plugin_name = plugin_name
        worker.plugin_dict = self.plugin_dict

        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.start()
        thread.finished.connect(lambda: self.uninstall_button_creation(plugin_name))
        thread.finished.connect(lambda: self.Installed(plugin_name))
    
    def Installed(self, plugin_name):
        row = list(self.plugin_dict.keys()).index(plugin_name)
        install_label = QTableWidgetItem("Installed")
        install_label.setFlags(Qt.ItemIsEnabled)
        install_label.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.tableWidget.setItem(row, 3, install_label)

class CustomDialog(QDialog):
    def __init__(self, plugin_name, plugin_info):
        super().__init__()
        self.name = plugin_name
        self.setWindowTitle("Manage")
        self.setGeometry(0, 0, 500, 200) 
        self.plugin_info = plugin_info
        self.install_url =  self.plugin_info["url"]

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
        r = client.get(f"http://127.0.0.1:8000/plugin_manager/update/{plugin_name}/{version}")
        # current_tag = self.getVersion()
        version_item = QTableWidgetItem(f"Current Version: {version}")
        version_item.setFlags(Qt.ItemIsEnabled)
        self.tableWidget.setItem(0, 0, version_item)
        print("Updated", plugin_name, "to version", version)

    def version_management(self):
        tag_list = []
        if ".git" in self.install_url:
            origin_folder = os.path.dirname(__file__)
            os.chdir(os.path.join(origin_folder, "plugin", self.name))
            tags = subprocess.check_output("git tag".split()).decode("utf-8")
            os.chdir(origin_folder)
            for label in tags.split("\n")[:-1]:
                tag_list.append(label)
        else:
            tag_list.append(self.install_url.split("/")[-1].split("-")[1].split(".")[0])
            # tag_list.append("No Versioning")
        return tag_list

    def createTable(self): 
        self.tableWidget = QTableWidget() 
        row_count = 2
        column_count = 3

        self.tableWidget.setRowCount(row_count)  
        self.tableWidget.setColumnCount(column_count) 
        self.button_dict = {}  
        current_tag = self.getVersion()
        cur_ver_item = QTableWidgetItem(f"Current Version: {current_tag}")
        avail_item = QTableWidgetItem("Available Versions")
        cur_ver_item.setFlags(Qt.ItemIsEnabled)
        avail_item.setFlags(Qt.ItemIsEnabled)
        self.tableWidget.setItem(0, 0, cur_ver_item)
        self.tableWidget.setItem(0, 1, avail_item)
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
        if ".git" in self.install_url:
            origin_folder = os.path.join(fastapi_launcher_path, self.name)
            os.chdir(origin_folder)
            try:
                tag = subprocess.check_output("git describe --tags".split()).decode("utf-8").split("\n")[0]
            except:
                tag = "0.0.0"
            os.chdir(os.path.dirname(__file__))
        else:
            tag = self.install_url.split("/")[-1].split("-")[1].split(".")[0]
        # print(tag)
        return tag

class Updater(QWidget):
    def __init__(self):
        super().__init__()
        # self.name = plugin_name
        self.setWindowTitle("Update")
        self.setGeometry(100, 100, 500, 200) 


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

        r = client.get(f"http://127.0.0.1:8000/plugin_manager/update/DeepMake/{version}")
        # print(p.communicate())
        current_tag = self.getVersion()
        cur_ver_item = QTableWidgetItem(f"Current Version: {current_tag}")
        cur_ver_item.setFlags(Qt.ItemIsEnabled)
        self.tableWidget.setItem(0, 0, cur_ver_item)
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

        cur_ver_item = QTableWidgetItem(f"Current Version: {current_tag}")
        avail_item = QTableWidgetItem("Available Versions")
        cur_ver_item.setFlags(Qt.ItemIsEnabled)
        avail_item.setFlags(Qt.ItemIsEnabled)

        self.tableWidget.setItem(0, 0, cur_ver_item)
        self.tableWidget.setItem(0, 1, avail_item)
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
    
class ReportIssueDialog(QWidget):
    def __init__(self, logFilePath=None):
        super().__init__()
        self.logFilePath = logFilePath
        print(f"Initialized with logFilePath: {self.logFilePath}")
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Report Issue')
        self.setGeometry(100, 100, 600, 300)
        layout = QVBoxLayout()

        layout.addWidget(QLabel('Error information:'))
        self.errorInfoTextEdit = QTextEdit()
        self.errorInfoTextEdit.setPlaceholderText("Describe the error or issue...")
        layout.addWidget(self.errorInfoTextEdit)

        layout.addWidget(QLabel('Additional information to include:'))
        self.additionalInfoTextEdit = QTextEdit()
        self.additionalInfoTextEdit.setPlaceholderText('Any extra details to help understand the issue...')
        layout.addWidget(self.additionalInfoTextEdit)

        self.attachLogCheckbox = QCheckBox("Attach log file")
        if self.logFilePath and os.path.exists(self.logFilePath) and os.path.getsize(self.logFilePath) > 0:
            self.attachLogCheckbox.setVisible(True)
        else:
            self.attachLogCheckbox.setVisible(False)
        layout.addWidget(self.attachLogCheckbox)

        layout.addWidget(QLabel('For immediate support you can join our Discord:'))
        self.discordButton = QPushButton()
        self.discordButton.setIcon(QIcon('Discord.png'))
        self.discordButton.setIconSize(QPixmap('Discord.png').size())
        self.discordButton.clicked.connect(self.joinDiscord)
        layout.addWidget(self.discordButton)

        self.sendReportButton = QPushButton('Send')
        self.sendReportButton.clicked.connect(self.sendReport)
        layout.addWidget(self.sendReportButton)

        self.setLayout(layout)

    def sendReport(self):
        errorInfo = self.errorInfoTextEdit.toPlainText()
        additionalInfo = self.additionalInfoTextEdit.toPlainText()
        attachLog = self.attachLogCheckbox.isChecked()
        print(f"Sending report with error info: '{errorInfo}' and additional info: '{additionalInfo}', attach log: {attachLog}")

        data = {'description': f"Error Info: {errorInfo}\nAdditional Info: {additionalInfo}"}
        print(data)
        if attachLog and self.logFilePath:
            print(f"Attaching log file at: {self.logFilePath}")
            data['log_file_path'] = self.logFilePath

        try:
            response = requests.post("http://127.0.0.1:8000/report/", data=data)
            print("Response Status Code:", response.status_code)
            if response.ok:
                print("Report sent successfully.")
            else:
                print(f"Failed to send report. Status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error sending report: {e}")

    def joinDiscord(self):
        webbrowser.open('https://discord.gg/U7FymgCM')


class LoginWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.backend_url = "http://localhost:8000"
        self.initUI()
        self.check_login()

    def initUI(self):
        self.layout = QVBoxLayout()

        # Login Section
        self.loginSection = QVBoxLayout()
        loginTitle = QLabel('Login to Deepmake')
        loginTitle.setStyleSheet('font-size: 18px; font-weight: bold;')

        emailLayout = QHBoxLayout()
        emailLabel = QLabel('Email')
        self.emailInput = QLineEdit()
        self.emailInput.setPlaceholderText('Textbox for Email')
        emailLayout.addWidget(emailLabel)
        emailLayout.addWidget(self.emailInput)

        passwordLayout = QHBoxLayout()
        passwordLabel = QLabel('Password')
        self.passwordInput = QLineEdit()
        self.passwordInput.setPlaceholderText('Textbox for Password')
        self.passwordInput.setEchoMode(QLineEdit.EchoMode.Password)
        passwordLayout.addWidget(passwordLabel)
        passwordLayout.addWidget(self.passwordInput)

        self.loginButton = QPushButton('Login')
        self.loginButton.clicked.connect(self.login)

        self.loginSection.addWidget(loginTitle)
        self.loginSection.addLayout(emailLayout)
        self.loginSection.addLayout(passwordLayout)
        self.loginSection.addWidget(self.loginButton)

        # Logged In Section
        self.loggedInSection = QVBoxLayout()
        self.loggedInLabel = QLabel('Logged in as ')
        self.loggedInLabel.setVisible(False)  # Hide until logged in
        self.logoutButton = QPushButton('Logout')
        self.logoutButton.clicked.connect(self.logout)
        self.logoutButton.setVisible(False)  # Hide until logged in

        self.loggedInSection.addWidget(self.loggedInLabel)
        self.loggedInSection.addWidget(self.logoutButton)

        # Add sections to the main layout
        self.layout.addLayout(self.loginSection)
        self.layout.addLayout(self.loggedInSection)
        self.setLayout(self.layout)

    def check_login(self):
        try:
            response = requests.get(f"{self.backend_url}/login/status")
            print(f"Checking login status: {response.json()}")
            if response.status_code == 200 and response.json()['logged_in']:
                user_info = response.json()
                self.loggedInLabel.setText(f'Logged in as {user_info.get("username", "Unknown")}')
                self.toggleLoginState(True)
        except requests.exceptions.RequestException as e:
            print(f"Failed to check login status: {e}")

    def login(self):
        username = self.emailInput.text()
        password = self.passwordInput.text()
        try:
            url = f"{self.backend_url}/login/login?username={username}&password={password}"
            response = requests.post(url)
            print(f"Login response: {response.json()}")
            if response.status_code == 200:
                self.loggedInLabel.setText(f'Logged in as {username}')
                self.toggleLoginState(True)
            else:
                print(response.json().get("message", "Login failed"))
        except requests.exceptions.RequestException as e:
            print(f"Login failed: {e}")

    def logout(self):
        try:
            response = requests.post(f"{self.backend_url}/login/logout")
            if response.status_code == 200:
                self.toggleLoginState(False)
        except requests.exceptions.RequestException as e:
            print(f"Logout failed: {e}")

    def toggleLoginState(self, loggedIn):
        self.loginSection.setEnabled(not loggedIn)
        self.loggedInLabel.setVisible(loggedIn)
        self.logoutButton.setVisible(loggedIn)
        if not loggedIn:
            self.loggedInLabel.setText('')
            self.emailInput.clear()
            self.passwordInput.clear()