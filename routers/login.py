from fastapi import APIRouter, FastAPI, Depends, Request, Header
import requests

router = APIRouter()
auth = None
client = requests.Session()

# @router.get("/")
# def some_router_function(request: Request):
#     global auth
#     auth = request.app.state.resource
#     return {"auth": auth}

@router.get("/login/status")
async def get_login_status():
    auth_check()
    return {"logged_in": auth.logged_in}

def auth_check():
    
    global auth
    print("hello")
    r = client.get(f"http://127.0.0.1:8000/plugins/get_list")
    print(r.json())
    if auth is None:
        r = client.get("http://127.0.0.1:8000/app-state-data", timeout=10)

    # auth = r.json()

    print("authenticator:", auth)

@router.post("/login/login")
async def login(username: str, password: str):

    if auth.login_with_credentials(username, password):
        return {"status": "success", "message": "Logged in successfully"}
    else:
        return {"status": "failed", "message": "Login failed"}

@router.post("/login/logout")
async def logout():

    auth.logout()
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/login/username")
async def get_username():
    return {"username": auth.username}

@router.get("/login/get_url")
async def get_file(url: str):

    return auth.get_url(url)

@router.get("/login/check_login")
async def check_login():
    if auth.logged_in:
        user = auth.get_user_info()
        return {'logged_in': True, 'email': user['email'], 'roles': user['app_metadata']['roles']}
    else:
        return {'logged_in': False}