from pydantic import BaseModel


class Customer(BaseModel):
    """Customer model for the customer.yaml file."""

    id: int
    name: str
    email: str
    phone: str
    website: str | None = None
    address: dict

    @property
    def street(self):
        return self.address["street"]

    @property
    def zip(self):
        return self.address["zip"]

    @property
    def city(self):
        return self.address["city"]
