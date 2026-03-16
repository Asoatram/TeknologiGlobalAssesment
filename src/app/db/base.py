from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so they are registered on Base.metadata.
from app import models  # noqa: E402,F401
