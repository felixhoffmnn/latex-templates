from pydantic import BaseModel

from src.models import Address


class Location(BaseModel):
    """References are used to add additional information to the letter.

    For example, the reference could be a customer number or a project name.
    """

    key: str
    value: str | int


class Letter(BaseModel):
    """Addressee model for a letter."""

    recipient: Address
    location: list[Location] | None = None
    place: str | None = None
    subject: str
    opening: str = "Sehr geehrte Damen und Herren,"
    closing: str = "Mit freundlichen Grüßen,"
