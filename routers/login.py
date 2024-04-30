from fastapi import APIRouter, FastAPI, Depends, Request, Header
import requests
from auth_handler import auth_handler as auth
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

router = APIRouter()
client = requests.Session()

# @router.get("/")
# def some_router_function(request: Request):
#     global auth
#     auth = request.app.state.resource
#     return {"auth": auth}

@router.get("/status")
async def get_login_status():
    print(auth.logged_in)
    return {"logged_in": auth.logged_in}

@router.post("/login")
async def login(request: LoginRequest):
    if auth.login_with_credentials(request.username, request.password):
        return {"status": "success", "message": "Logged in successfully"}
    else:
        return {"status": "failed", "message": "Login failed"}

@router.get("/logout")
async def logout():

    auth.logout()
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/username")
async def get_username():
    return {"username": auth.username}

@router.get("/get_url")
async def get_file(url: str):

    return auth.get_url(url)

@router.get("/check_login")
async def check_login():
    if auth.logged_in:
        user = auth.get_user_info()
        return {'logged_in': True, 'email': user['email'], 'roles': auth.roles}
    else:
        return {'logged_in': False}

@router.get("/subscription_level")
async def subscription_level():
    return {"status": "success", "subscription_level": auth.permission_level()}