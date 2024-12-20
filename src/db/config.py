import os
from dotenv import load_dotenv



POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
POSTGRES_SERVER = "localhost"
POSTGRES_PORT = "5431"
POSTGRES_DB = "postgres"
POSTGRES_URL = os.getenv("POSTGRES_URL", f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}")