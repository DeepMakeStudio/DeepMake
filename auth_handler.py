# Website login class, handles authentication of users, refreshing the jwt key as needed, and requesting user information
import jwt
import requests
import time
from storage_db import storage_db

class AuthHandler():
    def __init__(self, refresh_token = None, JWT = None, username = None, password = None):
        self.JWT = None
        self.refresh_token = None
        self.storage = storage_db()

        if JWT is not None:
            self.JWT = JWT
        if username is not None and password is not None:
            self.login_with_credentials(username, password)
        elif refresh_token is not None:
            self.refresh_token = refresh_token
        elif self.refresh_token is None:
            auth_token = self.storage.retrieve_data('auth')
            if auth_token:
                self.refresh_token = auth_token['refresh_token']
                if JWT in auth_token:
                    self.JWT = auth_token['JWT']
                    self.validate_jwt()
                else:
                    self.refresh_login()


    @property
    def decoded_jwt(self):
        return jwt.decode(self.JWT, options={"verify_signature": False})

    @property
    def logged_in(self):
        if self.JWT is not None:
            return self.validate_jwt()
        else:
            return False
    
    @property
    def username(self):
        if self.logged_in:
            return self.decoded_jwt['email']
        else:
            return None
    
    @property
    def roles(self):
        return self.check_roles()

    def update_jwt(self, jwt_token):
        self.JWT = jwt_token

    def login_with_credentials(self, username, password):
        credentials = {'username': username, 'password': password, 'grant_type': 'password'}
        login_response = requests.post('https://deepmake.com/.netlify/identity/token',data=credentials)
        if login_response.status_code == 200:
            self.refresh_token = login_response.json()['refresh_token']
            self.update_jwt(login_response.json()['access_token'])
            self.storage.store_data('auth', {'refresh_token': self.refresh_token, 'JWT': login_response.json()['access_token']})
            return True
        else:
            return False

    def refresh_login(self):
        if self.refresh_token is None:
            return False
        refresh_response = requests.post('https://deepmake.com/.netlify/identity/token',data={'refresh_token': self.refresh_token, 'grant_type': 'refresh_token'})
        if refresh_response.status_code == 200:
            self.refresh_token = refresh_response.json()['refresh_token']
            self.update_jwt(refresh_response.json()['access_token'])
            self.storage.store_data('auth', {'refresh_token': self.refresh_token, 'JWT': refresh_response.json()['access_token']})
            return True
        else:
            return False
    
    def get_user_info(self):
        user_info = requests.get('https://deepmake.com/.netlify/identity/user', headers={'Authorization': 'Bearer ' + self.JWT})
        if user_info.status_code == 200:
            return user_info.json()
        else:
            return False
        
    def validate_jwt(self):
        if self.JWT is None:
            return False
        if self.decoded_jwt['exp'] < time.time():
            return self.refresh_login()
        else:
            return True

    def get_url(self, url):
        self.validate_jwt()
        headers = {'Authorization': f'Bearer {self.JWT}', 'Cookie': f'nf_jwt={self.JWT}'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:         
            return response.json()
        else:
            return False

    def check_roles(self):
        if not self.logged_in:
            return []
        if not self.validate_jwt():
            return []
        user_info = self.get_user_info()
        if 'roles' not in user_info['app_metadata']:
            return []
        return user_info['app_metadata']['roles']

    def check_permissions(self, level=1):
        if not self.logged_in:
            return False
        if level == 0:
            return True
        roles = self.check_roles()
        if len(roles) > 0:
            return True
        else:
            return False

    def permission_level(self):
        if not self.logged_in:
            return False
        roles = self.check_roles()
        if len(roles) > 0:
            return 1
        else:
            return 0

    def logout(self):
        self.JWT = None
        self.refresh_token = None
        self.storage.store_data('auth', {})
        return True

auth_handler = AuthHandler()