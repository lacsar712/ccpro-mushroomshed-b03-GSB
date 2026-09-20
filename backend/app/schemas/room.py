from marshmallow import Schema, fields, validate


ROOM_STATUSES = ("fruiting", "idle", "sanitize")


class RoomCreateSchema(Schema):
    shed_id = fields.Int(required=True, data_key="shedId")
    room_code = fields.Str(required=True, data_key="roomCode", validate=validate.Length(min=1, max=32))
    species = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    capacity_bags = fields.Int(required=True, data_key="capacityBags", validate=validate.Range(min=1))
    status = fields.Str(required=True, validate=validate.OneOf(ROOM_STATUSES))


class RoomUpdateSchema(Schema):
    species = fields.Str(required=False, validate=validate.Length(min=1, max=64))
    status = fields.Str(required=False, validate=validate.OneOf(ROOM_STATUSES))


class SpeciesSealOutSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(data_key="roomId")
    species = fields.Str()
    sealed_at = fields.DateTime(data_key="sealedAt")
    released_at = fields.DateTime(allow_none=True, data_key="releasedAt")
    release_reason = fields.Str(allow_none=True, data_key="releaseReason")


class RoomOutSchema(Schema):
    id = fields.Int(dump_only=True)
    shed_id = fields.Int(data_key="shedId")
    room_code = fields.Str(data_key="roomCode")
    species = fields.Str()
    capacity_bags = fields.Int(data_key="capacityBags")
    status = fields.Str()
