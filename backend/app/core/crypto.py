import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


def _get_key() -> bytes:
    key_b64 = settings.encryption_key
    if not key_b64:
        raise RuntimeError("ENCRYPTION_KEY environment variable is required. Generate one with scripts/generate-keys.sh")
    raw = base64.b64decode(key_b64.encode())
    if len(raw) != 32:
        raise ValueError("ENCRYPTION_KEY must be 32 bytes when base64-decoded")
    return raw


def encrypt(plaintext: str) -> str:
    key = _get_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt(ciphertext: str) -> str:
    key = _get_key()
    raw = base64.b64decode(ciphertext.encode())
    if len(raw) < 12:
        raise ValueError("Invalid ciphertext: too short")
    nonce = raw[:12]
    ct = raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode()
