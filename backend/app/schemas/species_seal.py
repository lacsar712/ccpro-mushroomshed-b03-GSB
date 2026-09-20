from marshmallow import Schema, ValidationError, fields, validates


class SpeciesSealOutSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(data_key="roomId")
    species = fields.Str()
    sealed_at = fields.DateTime(data_key="sealedAt")
    released_at = fields.DateTime(data_key="releasedAt", allow_none=True)
    release_reason = fields.Str(data_key="releaseReason", allow_none=True)
    released_by = fields.Str(data_key="releasedBy", allow_none=True)


class SpeciesSealReleaseSchema(Schema):
    reason = fields.Str(required=True)

    @validates("reason")
    def _reason_not_blank(self, value, **kwargs):
        if not value or not value.strip():
            raise ValidationError("解封原因不能空白")
