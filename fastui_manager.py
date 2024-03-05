from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastui import FastUI, AnyComponent, prebuilt_html, components as c
from fastui.components.display import DisplayMode, DisplayLookup
from fastui.events import GoToEvent, BackEvent
from pydantic import BaseModel, Field
import json
import os
import subprocess
import sys

app = FastAPI()

with open(os.path.join(os.path.dirname(__file__), "gui_info.json")) as f:
    plugin_dict = json.load(f)

class Plugin(BaseModel):
    name: str
    description: str
    version: str
    install: str

plugin_list = []
for plugin in plugin_dict["plugin"].keys():
    plugin_info = plugin_dict["plugin"][plugin]
    install_message = "Install"
    if plugin in os.listdir(os.path.join(os.path.dirname(__file__), "plugin")):
        install_message = "Manage"
    description = plugin_info["Description"]
    version = plugin_info["Version"]
    plugin_list.append(Plugin(name=plugin, description=description, version=version, install=install_message))



@app.get("/api/", response_model=FastUI, response_model_exclude_none=True)
def users_table() -> list[AnyComponent]:
    """
    Show a table of four users, `/api` is the endpoint the frontend will connect to
    when a user visits `/` to fetch components to render.
    """
    return [
        c.Page(  # Page provides a basic container for components
            components=[
                c.Heading(text='Plugin Manager', level=2),  # renders `<h2>Users</h2>`
                c.Table(
                    data=plugin_list,
                    # define two columns for the table
                    columns=[
                        # the first is the users, name rendered as a link to their profile
                        DisplayLookup(field='name'),
                        # the second is the date of birth, rendered as a date
                        DisplayLookup(field='description'),
                        DisplayLookup(field='version'),
                        DisplayLookup(field="install", on_click=GoToEvent(url='/install/{name}/')),
                    ],
                ),
            ]
        ),
    ]



@app.get("/api/install/{plugin_name}/", response_model=FastUI, response_model_exclude_none=True)
def install_plugin(plugin_name: str):
    clone_link = plugin_dict["plugin"][plugin_name]["url"] + ".git"
    folder_path = os.path.join(os.path.dirname(__file__), "plugin", plugin_name)
    if sys.platform != "win32":
        p = subprocess.Popen(f"git clone {clone_link} {folder_path}".split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        p = subprocess.Popen(f"git clone {clone_link} {folder_path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    if "already exists" in err.decode("utf-8"):
        print("Plugin already installed")
    else:
        print("Installed", plugin_name)
    # return
    # return GoToEvent(url="/api/")
    return GoToEvent(url='/')

@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    """Simple HTML page which serves the React app, comes last as it matches all paths."""
    return HTMLResponse(prebuilt_html(title='FastUI Demo'))