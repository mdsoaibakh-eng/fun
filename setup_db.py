import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# Parse database URL to get credentials
# Format: mysql+pymysql://root:@localhost/college_event_db
db_url = os.getenv('DATABASE_URL')
if not db_url.startswith('mysql+pymysql://'):
    print("Not a MySQL URL")
    exit(1)

parts = db_url.replace('mysql+pymysql://', '').split('@')
creds = parts[0].split(':')
user = creds[0]
password = creds[1] if len(creds) > 1 else ''
host_db = parts[1].split('/')
host = host_db[0]
db_name = host_db[1]

print(f"Connecting to {host} as {user}...")

try:
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password
    )
    cursor = connection.cursor()
    
    print(f"Creating database {db_name} if not exists...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    print("Database created successfully.")
    
    cursor.close()
    connection.close()
except Exception as e:
    print(f"Error: {e}")
