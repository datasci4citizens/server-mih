import os
from dotenv import load_dotenv


load_dotenv()
client_id     = '249629522262-9g6sohr4eobuv78nc0q86edkoa4n3nvm.apps.googleusercontent.com'
client_secret = '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'
CLIENT_ID = os.environ.get(client_id, None)
CLIENT_SECRET = os.environ.get(client_secret, None)

POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"
POSTGRES_SERVER = "localhost"
POSTGRES_PORT = "5431"
POSTGRES_DB = "postgres"
POSTGRES_URL = os.getenv("POSTGRES_URL", f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}")