import sys
import os
import sqlite3
import json
from fastapi import HTTPException

if sys.platform == "win32":
    storage_folder = os.path.join(os.getenv('APPDATA'),"DeepMake")
elif sys.platform == "darwin":
    storage_folder = os.path.join(os.getenv('HOME'),"Library","Application Support","DeepMake")
elif sys.platform == "linux":
    storage_folder = os.path.join(os.getenv('HOME'),".local", "DeepMake")

def store_data(key: str, item: dict):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    value = json.dumps(dict(item))
    cursor.execute("REPLACE INTO key_value_store (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    return {"message": "Data stored successfully"}

def retrieve_data(key: str):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM key_value_store WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    data = json.loads(row[0])
    if row:
        return data
    raise HTTPException(status_code=404, detail="Key not found")

def delete_data(key: str):
    conn = sqlite3.connect(os.path.join(storage_folder, 'data_storage.db'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM key_value_store WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    return {"message": "Data deleted successfully"}
