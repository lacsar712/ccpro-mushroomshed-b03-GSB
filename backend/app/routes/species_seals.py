from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import Schema, ValidationError, fields, validate

from app.database import SessionLocal
from app.models.species_seal import SpeciesSeal
from app.models.user import User
from app.schemas.room import SpeciesSealOutSchema
from app.utils import validation_error_response

bp = Blueprint("species_seals", __name__, url_prefix="/api/species-seals")

seal_out = SpeciesSealOutSchema()


class SealReleaseSchema(Schema):
    reason = fields.Str(required=True, validate=validate.Length(min=1, max=500))


@bp.post("/<int:seal_id>/release")
@jwt_required()
def release_seal(seal_id: int):
    db = SessionLocal()
    try:
        username = get_jwt_identity()
        user = db.query(User).filter(User.username == username).first()
        # 只有 admin（场长）能解除物种封印，fruiter 一律 403
        if not user or user.role != "admin":
            return jsonify({"detail": "仅场长（admin）可解除物种封印"}), 403

        try:
            data = SealReleaseSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        reason = data["reason"].strip()
        if not reason:
            return jsonify({"detail": "解封原因不能空白"}), 400

        seal = db.query(SpeciesSeal).filter(SpeciesSeal.id == seal_id).first()
        if not seal:
            return jsonify({"detail": "封印不存在"}), 404
        if seal.released_at is not None:
            return (
                jsonify(
                    {
                        "detail": "该封印已解除",
                        "sealId": seal.id,
                        "releasedAt": seal_out.dump(seal)["releasedAt"],
                    }
                ),
                409,
            )

        seal.released_at = datetime.now(timezone.utc)
        seal.release_reason = reason
        db.commit()
        db.refresh(seal)
        return jsonify(seal_out.dump(seal))
    finally:
        db.close()
