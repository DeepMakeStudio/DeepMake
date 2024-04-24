from fastapi import APIRouter, FastAPI, Depends, Request, Header
import requests
from shared_state import shared_state

router = APIRouter()
client = requests.Session()

@router.get("/get-value/", tags=["login"])
def get_value():
    return {"value": shared_state.get_value()}

@router.post("/set-value/", tags=["login"])
def set_value(value: str):
    shared_state.set_value(value)
    return {"message": "Value set successfully"}

# @router.get("/")
# def some_router_function(request: Request):
#     global auth
#     auth = request.app.state.resource
#     return {"auth": auth}

@router.get("/login/status", tags=["login"])
async def get_login_status():
    global auth
    auth = get_value()["value"]
    return {"logged_in": auth.logged_in}

@router.post("/login/login", tags=["login"])
async def login(username: str, password: str):

    if auth.login_with_credentials(username, password):
        return {"status": "success", "message": "Logged in successfully"}
    else:
        return {"status": "failed", "message": "Login failed"}

@router.post("/login/logout", tags=["login"])
async def logout():

    auth.logout()
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/login/username", tags=["login"])
async def get_username():
    return {"username": auth.username}

@router.get("/login/get_url", tags=["login"])
async def get_file(url: str):

    return auth.get_url(url)

@router.get("/login/check_login", tags=["login"])
async def check_login():
    if auth.logged_in:
        user = auth.get_user_info()
        return {'logged_in': True, 'email': user['email'], 'roles': user['app_metadata']['roles']}
    else:
        return {'logged_in': False}