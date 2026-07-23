from pydantic import BaseModel

from invoice_toolkit.models import Address


class Letter(BaseModel):
    """Letter frontmatter model containing recipient, subject, and formatting options."""

    recipient: Address
    subject: str
    opening: str = "Sehr geehrte Damen und Herren,"
    closing: str = "Mit freundlichen Grüßen,"
