from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.room import Room
from app.models.shed import Shed
from app.models.species_seal import SpeciesSeal
from app.schemas.room import (
    RoomCreateSchema,
    RoomOutSchema,
    RoomUpdateSchema,
    SpeciesSealOutSchema,
)
from app.utils import validation_error_response

bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")

create_schema = RoomCreateSchema()
update_schema = RoomUpdateSchema()
out_schema = RoomOutSchema()
out_many = RoomOutSchema(many=True)
seal_out = SpeciesSealOutSchema()


def _active_seal_map(db, room_ids):
    """返回 {room_id: SpeciesSeal}，只含 released_at 为空的封印。"""
    if not room_ids:
        return {}
    rows = (
        db.query(SpeciesSeal)
        .filter(SpeciesSeal.room_id.in_(room_ids), SpeciesSeal.released_at.is_(None))
        .all()
    )
    return {s.room_id: s for s in rows}


def _dump_room(room: Room, seal: SpeciesSeal | None = None) -> dict:
    data = out_schema.dump(room)
    data.update(
        {
            "sealId": seal.id if seal else None,
            "sealedSpecies": seal.species if seal else None,
            "sealedAt": seal_out.dump(seal)["sealedAt"] if seal else None,
        }
    )
    return data


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
        seals = _active_seal_map(db, [r.id for r in rows])
        return jsonify([_dump_room(r, seals.get(r.id)) for r in rows])
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
        # 以 fruiting 房态建档即进入出菇，按当时 species 封印
        if item.status == "fruiting":
            db.add(
                SpeciesSeal(
                    room=item,
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
        seal = (
            db.query(SpeciesSeal)
            .filter(SpeciesSeal.room_id == item.id, SpeciesSeal.released_at.is_(None))
            .first()
        )
        return jsonify(_dump_room(item, seal)), 201
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
        if not data:
            return jsonify({"detail": "没有可更新的字段"}), 400

        new_species = data.get("species")
        new_status = data.get("status")
        active_seal = (
            db.query(SpeciesSeal)
            .filter(SpeciesSeal.room_id == item.id, SpeciesSeal.released_at.is_(None))
            .first()
        )

        # 封印未解除时不允许改 species（即便同时改了房态，整笔请求拒绝）
        if new_species is not None and new_species != item.species and active_seal:
            return (
                jsonify(
                    {
                        "detail": "物种封印未解除，禁止修改品种",
                        "sealId": active_seal.id,
                    }
                ),
                409,
            )

        if new_species is not None:
            item.species = new_species

        entering_fruiting = new_status == "fruiting" and item.status != "fruiting"
        if new_status is not None:
            item.status = new_status

        # 再次进入 fruiting 会再封一张，物种以进入当时的 species 为准
        if entering_fruiting and not active_seal:
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
            return jsonify({"detail": "更新失败"}), 400
        db.refresh(item)
        seal = active_seal or (
            db.query(SpeciesSeal)
            .filter(SpeciesSeal.room_id == item.id, SpeciesSeal.released_at.is_(None))
            .first()
        )
        return jsonify(_dump_room(item, seal))
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
