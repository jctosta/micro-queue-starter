from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.settings import Settings
from app.models import User
import os
import json
from pathlib import Path

# Load users from the JSON file in the fixtures directory (root -> fixtures -> users.json)
ROOT_DIR = Path(__file__).parent.parent
user_file_path = os.path.join(ROOT_DIR, "fixtures", "users.json")
print(user_file_path)
with open(user_file_path, "r") as user_file:
    USERS = {user["api_key"]: User(**user) for user in json.load(user_file)}

api_key_header = APIKeyHeader(name="X-API-Key")
settings = Settings()


def validate_api_key(api_key: str = Security(api_key_header)) -> User:
    user = USERS.get(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return user
