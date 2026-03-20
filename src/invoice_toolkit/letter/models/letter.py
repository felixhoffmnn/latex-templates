"""Letter data models for recipient addressing and metadata."""

from pydantic import BaseModel

from invoice_toolkit.models import Address


class Location(BaseModel):
    """A key-value pair displayed in the letter's information block.

    For example, a customer number or a project name.
    """

    key: str
    value: str | int


class Letter(BaseModel):
    """Letter frontmatter model containing recipient, subject, and formatting options."""

    recipient: Address
    location: list[Location] | None = None
    place: str | None = None
    subject: str
    opening: str = "Sehr geehrte Damen und Herren,"
    closing: str = "Mit freundlichen Grüßen,"
