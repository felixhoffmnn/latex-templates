from pydantic import BaseModel, EmailStr, HttpUrl
from pydantic_extra_types.phone_numbers import PhoneNumber

from latex_templates.models import Address


class Customer(BaseModel):
    """Customer model for the customer.yaml file."""

    customer_id: int
    name: str
    company: str | None = None
    email: EmailStr
    phone: PhoneNumber
    url: HttpUrl | None = None
    address: Address

    # address needs to be initialized manually
    def __init__(self, **data):
        """Initialize the customer model."""
        data["address"] = {
            "street": data.get("street"),
            "zip": data.get("zip"),
            "city": data.get("city"),
            "country": data.get("country"),
        }
        super().__init__(**data)
