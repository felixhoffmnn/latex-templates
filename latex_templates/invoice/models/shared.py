from pydantic import BaseModel, Field


class Address(BaseModel):
    """Address model."""

    street: str
    zip: str
    city: str
    country: str | None = Field(None, pattern=r"^(DE|Germany|Deutschland)$")
