from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from app.database import SessionLocal
from app.models.species_seal import SpeciesSeal
from app.schemas.species_seal import SpeciesSealOutSchema, SpeciesSealReleaseSchema
from app.utils import admin_required, validation_error_response

bp = Blueprint("species_seals", __name__, url_prefix="/api/species-seals")

out_schema = SpeciesSealOutSchema()
release_schema = SpeciesSealReleaseSchema()


@bp.post("/<int:seal_id>/release")
@admin_required
def release_seal(seal_id: int):
    db = SessionLocal()
    try:
        seal = db.query(SpeciesSeal).filter(SpeciesSeal.id == seal_id).first()
        if not seal:
            return jsonify({"detail": "封印不存在"}), 404
        try:
            data = release_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        if seal.released_at is not None:
            return jsonify({"detail": "该封印已解除", "sealId": seal.id}), 409
        seal.released_at = datetime.now(timezone.utc)
        seal.release_reason = data["reason"].strip()
        seal.released_by = get_jwt_identity()
        db.commit()
        db.refresh(seal)
        return jsonify(out_schema.dump(seal))
    finally:
        db.close()
