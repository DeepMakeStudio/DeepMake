from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QComboBox, QSlider, QSizePolicy, QHBoxLayout, QVBoxLayout, QCheckBox, QDialog, QScrollArea, QDialogButtonBox, QLabel
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

class Window(QWidget):
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

        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.submit_config)
        self.layout.addWidget(submit_button) 
        self.setLayout(self.layout) 
        # self.setFixedSize(self.layout.sizeHint())


    def guiFromConfig(self, config):
        for key in config:
            value = config[key]
            print(type(value))  
            label = QLabel(key)
            self.layout.addWidget(label)
            if isinstance(value, str):
                # self.widget_dict[key] = QLineEdit(f"{value}")
                text_box = QLineEdit(f"{value}")
                print(key, text_box.text())
                # text_box.textChanged.connect(lambda key = key, text=text_box.text(): self.editConfig(key, text))
                text_box.textChanged.connect(lambda text, key = key: self.editConfig(key, text))
                # self.widget_dict[key] = text_box
                self.layout.addWidget(text_box) 
            elif isinstance(value, list):
                dropdown = QComboBox()
                for item in value:
                    dropdown.addItem(item)
                dropdown.setEditable(True)
                dropdown.currentTextChanged.connect(lambda text, key = key: self.editConfig(key, text))
                self.layout.addWidget(dropdown)
            elif isinstance(value, int):
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
        # self.layout.addWidget(QLabel("Run from CPU"))
        self.layout.addWidget(QCheckBox("Run from CPU"))
    def changeValue(self, label, value):
        label.setText(f"{value}")
    def editConfig(self, key, text):
        
        self.output_config[key] = text
        print(self.output_config)


    def submit_config(self):
        r = client.put(f"http://127.0.0.1:8000/plugins/set_config/{self.name}", json = self.output_config)
        print(r)
        print(r.text)

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


class CustomDialog(QDialog):
    def __init__(self, plugin_name):
        super().__init__()
        self.name = plugin_name
        self.setWindowTitle("Uninstaller")

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton("Uninstall", QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttonBox.addButton("Change Version", QDialogButtonBox.ButtonRole.RejectRole)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.version_management)

        self.layout = QVBoxLayout()
        # message = QLabel("Do you want to uninstall?")
        # self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)





app = QApplication(sys.argv)

window = Window("Diffusers")


apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")

window.setStyleSheet("QScrollBar::handle {background: #ffffff;} QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background: #ffffff;} QTableView {background-color: rgba(239,0,86,0.5); font-weight: bold;} QHeaderView::section {font-weight: bold; background-color: #7b3bff; color: #ffffff} QTableView::item:selected {background-color: #7b3bff; color: #ffffff;} QPushButton:pressed {color: #ffffff; background-color: #7b3bff;} QPushButton {color: #ffffff;}")

window.show()

sys.exit(app.exec())