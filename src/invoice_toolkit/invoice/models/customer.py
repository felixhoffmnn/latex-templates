from pydantic import BaseModel, EmailStr, HttpUrl
from pydantic_extra_types.phone_numbers import PhoneNumber

from invoice_toolkit.models import Address


class Customer(BaseModel):
    """Customer model for the customer CSV file."""

    customer_id: int
    company: str | None = None
    email: EmailStr
    phone: PhoneNumber
    url: HttpUrl | None = None
    buyer_reference: str | None = None
    address: Address

    # address needs to be initialized manually
    def __init__(self, **data):
        data["address"] = {
            "name": data.get("name"),
            "street": data.get("street"),
            "zip": data.get("zip"),
            "city": data.get("city"),
            "country": data.get("country"),
        }
        super().__init__(**data)
