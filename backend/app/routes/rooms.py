from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.room import Room
from app.models.shed import Shed
from app.models.species_seal import SpeciesSeal
from app.schemas.room import RoomCreateSchema, RoomOutSchema, RoomUpdateSchema
from app.utils import validation_error_response

bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")

create_schema = RoomCreateSchema()
update_schema = RoomUpdateSchema()
out_schema = RoomOutSchema()
out_many = RoomOutSchema(many=True)


def _active_seal(db, room_id: int):
    """同室同时只留一张 releasedAt 为空的封印。"""
    return (
        db.query(SpeciesSeal)
        .filter(SpeciesSeal.room_id == room_id, SpeciesSeal.released_at.is_(None))
        .first()
    )


def _attach_seals(db, rows):
    """给每行挂上未解封封印的 species / id（没有封印则为空）。"""
    ids = [r.id for r in rows]
    seals = {}
    if ids:
        for s in (
            db.query(SpeciesSeal)
            .filter(SpeciesSeal.room_id.in_(ids), SpeciesSeal.released_at.is_(None))
            .all()
        ):
            seals[s.room_id] = s
    for r in rows:
        active = seals.get(r.id)
        r.sealed_species = active.species if active else None
        r.seal_id = active.id if active else None
    return rows


@bp.get("")
@jwt_required()
def list_rooms():
    db = SessionLocal()
    try:
        shed_id = request.args.get("shedId", type=int)
        q = db.query(Room)
        if shed_id is not None:
            q = q.filter(Room.shed_id == shed_id)
        rows = q.order_by(Room.id).all()
        _attach_seals(db, rows)
        return jsonify(out_many.dump(rows))
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_room():
    db = SessionLocal()
    try:
        try:
            data = create_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        shed = db.query(Shed).filter(Shed.id == data["shed_id"]).first()
        if not shed:
            return jsonify({"detail": "菇房不存在"}), 400
        item = Room(
            shed_id=data["shed_id"],
            room_code=data["room_code"],
            species=data["species"],
            capacity_bags=data["capacity_bags"],
            status=data["status"],
        )
        db.add(item)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            return jsonify({"detail": "同菇房内出菇室编号已存在"}), 400
        # 直接以 fruiting 创建的出菇室，视同进入 fruiting，立即封印当时品种
        if item.status == "fruiting":
            db.add(
                SpeciesSeal(
                    room_id=item.id,
                    species=item.species,
                    sealed_at=datetime.now(timezone.utc),
                )
            )
        db.commit()
        db.refresh(item)
        _attach_seals(db, [item])
        return jsonify(out_schema.dump(item)), 201
    finally:
        db.close()


@bp.patch("/<int:room_id>")
@jwt_required()
def update_room(room_id: int):
    db = SessionLocal()
    try:
        item = db.query(Room).filter(Room.id == room_id).first()
        if not item:
            return jsonify({"detail": "出菇室不存在"}), 404
        try:
            data = update_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)

        seal = _active_seal(db, item.id)

        # 封印未解除时不许改 species：整单拒绝，库里的 species 保持原样
        new_species = data.get("species")
        if new_species is not None and new_species != item.species and seal is not None:
            return (
                jsonify(
                    {
                        "detail": f"品种已封印为「{seal.species}」，须由场长解封后才能修改",
                        "sealId": seal.id,
                    }
                ),
                409,
            )

        old_status = item.status
        if "room_code" in data:
            item.room_code = data["room_code"]
        if new_species is not None:
            item.species = new_species
        if "capacity_bags" in data:
            item.capacity_bags = data["capacity_bags"]
        if "status" in data:
            item.status = data["status"]

        # 进入 fruiting 时把当时的 species 抄进新封印；已有未解封封印则不重复封
        if item.status == "fruiting" and old_status != "fruiting" and seal is None:
            db.add(
                SpeciesSeal(
                    room_id=item.id,
                    species=item.species,
                    sealed_at=datetime.now(timezone.utc),
                )
            )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return jsonify({"detail": "同菇房内出菇室编号已存在"}), 400
        db.refresh(item)
        _attach_seals(db, [item])
        return jsonify(out_schema.dump(item))
    finally:
        db.close()


@bp.delete("/<int:room_id>")
@jwt_required()
def delete_room(room_id: int):
    db = SessionLocal()
    try:
        item = db.query(Room).filter(Room.id == room_id).first()
        if not item:
            return jsonify({"detail": "出菇室不存在"}), 404
        db.delete(item)
        db.commit()
        return "", 204
    finally:
        db.close()
