import os
import secrets
from pathlib import Path
from typing import Tuple

from cryptography.fernet import Fernet
from flask import current_app


def _get_cipher() -> Fernet:
    key = current_app.config.get("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not configured. Set a base64-encoded key in the environment before storing files."
        )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def save_encrypted(file_storage, user_id: str, prefix: str) -> Tuple[str, str]:
    uploads_root = Path(current_app.config["UPLOAD_FOLDER"]) / user_id
    uploads_root.mkdir(parents=True, exist_ok=True)

    random_suffix = secrets.token_hex(8)
    stored_filename = f"{prefix}_{random_suffix}"
    stored_path = uploads_root / stored_filename

    cipher = _get_cipher()
    data = file_storage.read()
    encrypted = cipher.encrypt(data)

    with stored_path.open("wb") as f:
        f.write(encrypted)

    file_storage.stream.seek(0)
    return stored_filename, str(stored_path)


def load_decrypted(path: str) -> bytes:
    cipher = _get_cipher()
    with open(path, "rb") as f:
        encrypted = f.read()
    return cipher.decrypt(encrypted)
