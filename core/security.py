from cryptography.fernet import Fernet

_fernet: Fernet | None = None


def init_fernet(key: str):
    global _fernet
    _fernet = Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(text: str) -> str:
    return _fernet.encrypt(text.encode()).decode()


def decrypt(text: str) -> str:
    return _fernet.decrypt(text.encode()).decode()
