import sys
import requests
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoginWidget()
    window.show()
    sys.exit(app.exec())

