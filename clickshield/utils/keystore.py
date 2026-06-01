from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_TARGET_NAME = "ClickShield/OpenAIAPIKey"


def save_api_key(key: str) -> bool:
    """Stores the API key in Windows Credential Manager. Returns True on success."""
    try:
        import win32cred
        win32cred.CredWrite(
            {
                "Type": win32cred.CRED_TYPE_GENERIC,
                "TargetName": _TARGET_NAME,
                "CredentialBlob": key,
                "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                "UserName": "clickshield",
            }
        )
        logger.debug("API key saved to Windows Credential Manager.")
        return True
    except Exception as exc:
        logger.warning("Could not save API key to Credential Manager: %s", exc)
        return False


def load_api_key() -> Optional[str]:
    """Loads the API key from Windows Credential Manager. Returns None if not found."""
    try:
        import win32cred
        cred = win32cred.CredRead(_TARGET_NAME, win32cred.CRED_TYPE_GENERIC)
        blob = cred["CredentialBlob"]
        # win32cred returns CredentialBlob as UTF-16LE bytes on Windows
        if isinstance(blob, bytes):
            return blob.decode("utf-16-le").rstrip("\x00")
        return blob
    except Exception:
        return None


def delete_api_key() -> None:
    try:
        import win32cred
        win32cred.CredDelete(_TARGET_NAME, win32cred.CRED_TYPE_GENERIC)
    except Exception:
        pass


def has_api_key() -> bool:
    return load_api_key() is not None
