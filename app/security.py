import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status


def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    admin_token = os.getenv("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Configure ADMIN_TOKEN para habilitar a gestão.")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, admin_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave administrativa inválida.")
