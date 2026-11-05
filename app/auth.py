import json
from pathlib import Path

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.models import User

USERS_FILE = Path(__file__).parent.parent / "fixtures" / "users.json"
USERS = {
    user.api_key: user
    for user in (User(**raw) for raw in json.loads(USERS_FILE.read_text()))
}

api_key_header = APIKeyHeader(name="X-API-Key")


def validate_api_key(api_key: str = Security(api_key_header)) -> User:
    user = USERS.get(api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return user
