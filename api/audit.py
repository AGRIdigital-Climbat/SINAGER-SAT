import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from .database import SessionLocal
from .auth.jwt import verify_token

URL_APP_MAP = [
    ("/api/v1/rea/", 4),
    ("/api/v1/edan/", 1),
    ("/api/v1/usuarios/", 9),
    ("/api/v1/shared/", 9),
    ("/api/v1/auth/", 9),
    ("/api/v1/upload/", 4),
]

METHOD_ACTION = {"POST": "CREATE", "PUT": "UPDATE", "DELETE": "DELETE"}


def _get_id_aplicacion(path: str) -> int | None:
    for prefix, app_id in URL_APP_MAP:
        if path.startswith(prefix):
            return app_id
    return None


def _get_usuario_id(request: Request) -> int | None:
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    payload = verify_token(auth.removeprefix("Bearer "))
    if payload is None:
        return None
    sub = payload.get("sub")
    return int(sub) if sub else None


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "0.0.0.0"


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        if method not in METHOD_ACTION:
            return await call_next(request)

        path = request.url.path
        body_bytes = await request.body()
        try:
            body_data = json.loads(body_bytes) if body_bytes else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            body_data = {}

        response = await call_next(request)

        if response.status_code >= 400:
            return response

        id_usuario = _get_usuario_id(request)
        id_aplicacion = _get_id_aplicacion(path)
        if id_aplicacion is None:
            return response

        detalle = {"path": path, "method": method}
        if body_data:
            clean_body = {k: v for k, v in body_data.items() if k != "contrasena"}
            if clean_body:
                detalle["body"] = clean_body
        raw_query = dict(request.query_params)
        if raw_query:
            detalle["params"] = raw_query

        db = SessionLocal()
        try:
            db.execute(
                text("""
                    INSERT INTO usuarios.auditoria
                        (id_usuario, id_aplicacion, accion, detalle, ip_origen)
                    VALUES (:u, :a, :ac, :d, :ip)
                """),
                {
                    "u": id_usuario,
                    "a": id_aplicacion,
                    "ac": METHOD_ACTION[method],
                    "d": json.dumps(detalle),
                    "ip": _get_client_ip(request),
                },
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return response
