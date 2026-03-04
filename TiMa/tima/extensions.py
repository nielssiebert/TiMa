from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema


db = SQLAlchemy()


class BaseSchema(SQLAlchemyAutoSchema):
    class Meta:
        load_instance = True
        include_relationships = True


__all__ = ["db", "Schema", "BaseSchema"]
