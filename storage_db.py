import sys
import sqlite3
import json
import os
from supabase import create_client, Client

# Determine the storage folder based on the operating system
if sys.platform == "win32":
    storage_folder = os.path.join(os.getenv('APPDATA'), "DeepMake")
elif sys.platform == "darwin":
    storage_folder = os.path.join(os.getenv('HOME'), "Library", "Application Support", "DeepMake")
elif sys.platform == "linux":
    storage_folder = os.path.join(os.getenv('HOME'), ".local", "DeepMake")

# Create the storage folder if it doesn't exist
if not os.path.exists(storage_folder):
    os.mkdir(storage_folder)

class storage_db:
    def __init__(self, use_cloud=False):
        self.use_cloud = use_cloud
        self.storage_db = os.path.join(storage_folder, 'data_storage.db')
        if self.use_cloud:
            self.supabase_url = "https://jpstqtdzwacwqjucbpws.supabase.co"
            self.supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impwc3RxdGR6d2Fjd3FqdWNicHdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTU4ODAzMDYsImV4cCI6MjAzMTQ1NjMwNn0.tbartx9yDK9NBXWTxDgLF8M0MXUbkujXD6AN6KevHIs"
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        else:
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
        if self.use_cloud:
            try:
                value = json.dumps(dict(item))
                response = self.supabase.table('key_value_store').upsert({"key": key, "value": value}).execute()

                # Check if the response contains data, indicating a successful operation
                if hasattr(response, 'data') and response.data:
                    return True
            
                return False
            except Exception as e:
                print(f"Error storing data in Supabase: {e}")
                return False
        else:
            try:
                conn = sqlite3.connect(self.storage_db)
                cursor = conn.cursor()
                value = json.dumps(dict(item))
                cursor.execute("REPLACE INTO key_value_store (key, value) VALUES (?, ?)", (key, value))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error storing data in local SQLite: {e}")
                return False


    def retrieve_data(self, key: str):
        if self.use_cloud:
            try:
                response = self.supabase.table('key_value_store').select("value").eq("key", key).execute()
                if response.data:
                    data = json.loads(response.data[0]['value'])
                    return data
                return False
            except Exception as e:
                print(f"Error retrieving data from Supabase: {e}")
                return False
        else:
            try:
                conn = sqlite3.connect(self.storage_db)
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM key_value_store WHERE key = ?", (key,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    data = json.loads(row[0])
                    return data
                return False
            except Exception as e:
                print(f"Error retrieving data from local SQLite: {e}")
                return False

