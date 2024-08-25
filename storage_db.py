import sys
import sqlite3
import json
import os

if sys.platform == "win32":
    storage_folder = os.path.join(os.getenv('APPDATA'),"DeepMake")
elif sys.platform == "darwin":
    storage_folder = os.path.join(os.getenv('HOME'),"Library","Application Support","DeepMake")
elif sys.platform == "linux":
    storage_folder = os.path.join(os.getenv('HOME'),".local", "DeepMake")

# storage_folder =  "/opt/dlami/nvme/DeepMake" # Set storage folder for AWS instances

if not os.path.exists(storage_folder):
    os.mkdir(storage_folder)

class storage_db:
    def __init__(self):
        self.storage_db = os.path.join(storage_folder, 'data_storage.db')
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.storage_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS key_value_store (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        conn.close()

    def store_data(self, key: str, item: dict):
        try:
            conn = sqlite3.connect(self.storage_db)
            cursor = conn.cursor()
            value = json.dumps(dict(item))
            cursor.execute("REPLACE INTO key_value_store (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
            conn.close()
            return True
        except:
            return False

    def retrieve_data(self, key: str):
        conn = sqlite3.connect(self.storage_db)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM key_value_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            data = json.loads(row[0])
            return data
        return False
