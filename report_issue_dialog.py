from PyQt6.QtWidgets import QApplication, QVBoxLayout, QLabel, QTextEdit, QCheckBox, QPushButton, QWidget
from PyQt6.QtGui import QIcon, QPixmap
import webbrowser
import requests
import os  # Import os for file existence and size checks

class ReportIssueDialog(QWidget):
    def __init__(self, logFilePath=None):
        super().__init__()
        self.logFilePath = logFilePath   # Adjust this path to your log file
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Report Issue')
        self.setGeometry(100, 100, 600, 300)
        layout = QVBoxLayout()

        layout.addWidget(QLabel('Error information:'))
        self.errorInfoTextEdit = QTextEdit()
        self.errorInfoTextEdit.setPlaceholderText("Describe the error or issue...")
        layout.addWidget(self.errorInfoTextEdit)

        layout.addWidget(QLabel('Additional information to include'))
        self.additionalInfoTextEdit = QTextEdit()
        self.additionalInfoTextEdit.setPlaceholderText('Any extra details to help understand the issue...')
        layout.addWidget(self.additionalInfoTextEdit)

        self.attachLogCheckbox = QCheckBox("Attach log file")
        # Display the checkbox only if the log file exists and is not empty
        if self.logFilePath and os.path.exists(self.logFilePath) and os.path.getsize(self.logFilePath) > 0:
            self.attachLogCheckbox.setVisible(True)
        else:
            self.attachLogCheckbox.setVisible(False)
        layout.addWidget(self.attachLogCheckbox)

        # Dynamically adjust checkbox visibility based on log file existence and size
        #self.attachLogCheckbox.setVisible(os.path.exists(self.logFilePath) and os.path.getsize(self.logFilePath) > 0)
        #layout.addWidget(self.attachLogCheckbox)

        layout.addWidget(QLabel('For immediate support you can join our Discord:'))
        self.discordButton = QPushButton()
        self.discordButton.setIcon(QIcon('Discord.png'))  # Ensure the icon path is correct
        self.discordButton.setIconSize(QPixmap('Discord.png').size())  # Ensure the icon path is correct
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

        # Form data initialization
        data = {'description': f"Error Info: {errorInfo}\nAdditional Info: {additionalInfo}"}

        # Including log_file_path in the data if the checkbox is checked
        if attachLog and self.logFilePath:
            data['log_file_path'] = self.logFilePath

        try:
            response = requests.post("http://localhost:8000/ui/report-issue/", data=data)
            if response.ok:
                print("Report sent successfully.")
            else:
                print(f"Failed to send report. Status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error sending report: {e}")


    def joinDiscord(self):
        # Update this link with the actual Discord invite
        webbrowser.open('https://discord.gg/your_invite_link')

if __name__ == '__main__':
    #log_file_path = '/home/andresca94/DeepMake/test_log_file.json'
    app = QApplication([])
    window = ReportIssueDialog()
    #window = ReportIssueDialog(logFilePath=log_file_path)
    window.show()
    app.exec()





