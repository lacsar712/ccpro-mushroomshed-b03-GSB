from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from marshmallow import ValidationError

from app.database import SessionLocal
from app.models.user import User


def validation_error_response(err: ValidationError):
    messages = []
    for field, msgs in err.messages.items():
        if isinstance(msgs, list):
            for m in msgs:
                messages.append(f"{field}: {m}" if field != "_schema" else str(m))
        else:
            messages.append(f"{field}: {msgs}")
    detail = "; ".join(messages) if messages else "请求参数校验失败"
    return jsonify({"detail": detail}), 400


def admin_required(fn):
    """仅场长（admin）可访问；其他角色（如 fruiter）一律 403。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == get_jwt_identity()).first()
        finally:
            db.close()
        if not user:
            return jsonify({"detail": "无效或过期的令牌"}), 401
        if user.role != "admin":
            return jsonify({"detail": "仅场长（admin）可执行该操作"}), 403
        return fn(*args, **kwargs)

    return wrapper
