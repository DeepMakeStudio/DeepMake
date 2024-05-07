import os
import json
import sys
import subprocess 
from fastapi import APIRouter, Form, HTTPException
import requests
import io
import zipfile
import sentry_sdk
from sentry_sdk import capture_message, configure_scope
#from sentry_sdk.integrations.huey import HueyIntegration

router = APIRouter()

@router.post("/report/")
async def report_issue(description: str = Form(...), log_file_path: str = Form(None)):
    print("Received report issue request.")
    print(f"Description: {description}")

    try:
        with configure_scope() as scope:
            if log_file_path and os.path.isfile(log_file_path):
                with open(log_file_path, 'r') as log_file:
                    log_data = json.load(log_file)
                    log_contents = json.dumps(log_data, indent=4).encode()  # Encode the pretty JSON to bytes
                scope.add_attachment(bytes=log_contents, filename=os.path.basename(log_file_path), content_type="application/json")
                print("Log file attached successfully.")
            else:
                print("No log file was attached or log file does not exist.")

            capture_message("Issue report created by user\n" + str(description))
    except Exception as e:
        print(f"Error processing the report: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing the report: {e}")

    return {"message": "Issue reported successfully"}

"""
@router.post("/report/")
async def report_issue(description: str = Form(...), log_file_path: str = Form(None)):
    print("Received report issue request.")
    print(f"Description: {description}")

    try:
        with configure_scope() as scope:
            # Attach the description as a text snippet
            scope.add_attachment(bytes=description.encode(), filename="description.txt", content_type="text/plain")

            if log_file_path and os.path.isfile(log_file_path):
                # Attach the log file directly if it exists
                scope.add_attachment(path=log_file_path, content_type="text/plain")
                print("Log file attached successfully.")
            else:
                print("No log file was attached or log file does not exist.")

            # Capture the message once all attachments are added
            capture_message("Issue report processed")
    except Exception as e:
        print(f"Error processing the report: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing the report: {e}")

    return {"message": "Issue reported successfully"}
"""

"""
@router.post("/report/")
async def report_issue(description: str = Form(...), log_file_path: str = Form(None)):
    print("Received report issue request.")
    print(f"Description: {description}")
    #capture_message(description)  # Log the basic description first
    #print("Sentry captured the basic description.")

    if log_file_path and os.path.isfile(log_file_path):
        print(f"Log file path provided: {log_file_path}")
        try:
            with open(log_file_path, 'r') as file:
                log_contents = file.read()
            print("Log file read successfully. Attaching contents to Sentry.")
            # Use a scope to attach additional data to Sentry events
            with configure_scope() as scope:
                scope.set_extra("log_contents", log_contents)
                capture_message("Log file attached")  # This message will include the log_contents extra data
            print("Sentry captured the message with log contents.")
        except Exception as e:
            print(f"Error reading log file: {log_file_path}. Exception: {e}")
            # Log the exception with a scope, if needed
            with configure_scope() as scope:
                scope.set_extra("log_file_path", log_file_path)
                capture_message(f"Error reading log file: {e}")
            raise HTTPException(status_code=500, detail=f"Error reading log file: {e}")
    else:
        print("No log file was attached or log file does not exist.")
        capture_message("No log file was attached")

    return {"message": "Issue reported successfully"}
"""