from PyQt6.QtWidgets import QApplication,QProgressDialog, QWidget, QPushButton, QLineEdit, QComboBox, QSlider, QSizePolicy, QHBoxLayout, QVBoxLayout, QCheckBox, QDialog, QScrollArea, QDialogButtonBox, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from qt_material import apply_stylesheet
import os
import json
import subprocess
fastapi_launcher_path = os.path.join(os.path.dirname(__file__), "plugin")
import sys
import requests
import threading

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
            if isinstance(value, str):
                # self.widget_dict[key] = QLineEdit(f"{value}")
                text_box = QLineEdit(f"{value}")
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

    def submit_config(self):
        
        r = client.put(f"http://127.0.0.1:8000/plugins/set_config/{self.name}", json = self.output_config)
    
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




# class progressWorker(QObject):
#     finished = pyqtSignal()
#     progress = pyqtSignal(int)

#     progress_bar = QProgressDialog('Work in progress', '', 0, 10)
#     progress_bar.setWindowTitle("Submitting Configuration...")
#     progress_bar.setWindowModality(Qt.WindowModality.WindowModal)
#     progress_bar.show()
#     progress_bar.setValue(0)
#     def run(self):
#         """Long-running task."""
#         self.finished.emit()

# app = QApplication(sys.argv)

# window = ConfigGUI("Diffusers")
# apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")
# window.setStyleSheet("QScrollBar::handle {background: #ffffff;} QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background: #ffffff;} QTableView {background-color: rgba(239,0,86,0.5); font-weight: bold;} QHeaderView::section {font-weight: bold; background-color: #7b3bff; color: #ffffff} QTableView::item:selected {background-color: #7b3bff; color: #ffffff;} QPushButton:pressed {color: #ffffff; background-color: #7b3bff;} QPushButton {color: #ffffff;}")
# window.show()

# sys.exit(app.exec())