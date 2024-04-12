from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QProgressBar, QComboBox, QHBoxLayout, QListWidget, QHeaderView, QTableWidget, QVBoxLayout, QTableWidgetItem, QDialog, QScrollArea, QDialogButtonBox
import subprocess
import sys
from qt_material import apply_stylesheet

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

        p = subprocess.Popen(f"git checkout {version} ".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
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


# app = QApplication(sys.argv)

# window = Updater()

# apply_stylesheet(app, theme='dark_purple.xml', invert_secondary=False, css_file="gui.css")

# window.setStyleSheet("QScrollBar::handle {background: #ffffff;} QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background: #ffffff;} QTableView {background-color: rgba(239,0,86,0.5); font-weight: bold;} QHeaderView::section {font-weight: bold; background-color: #7b3bff; color: #ffffff} QTableView::item:selected {background-color: #7b3bff; color: #ffffff;} QPushButton:pressed {color: #ffffff; background-color: #7b3bff;} QPushButton {color: #ffffff;}")

# window.show()

# sys.exit(app.exec())