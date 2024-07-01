import datetime

from pydantic import BaseModel, Field


class Item(BaseModel):
    """Item model for an invoice file."""

    name: str
    description: str | None = None
    quantity: int = Field(1, ge=1)
    unit: str = Field("Stunde", pattern="^(Stunde|Stück|Monat)$")
    price: float = Field(0, ge=0)
    total: float | None = Field(None, ge=0)

    def __init__(self, **data):
        """Initialize the item model."""
        super().__init__(**data)
        self.total = self.price * self.quantity


class Invoice(BaseModel):
    """Invoice model for a invoice file."""

    customer_id: int = Field(ge=10000)
    invoice_id: int | None = Field(None, ge=1)
    invoice_number: str | None = Field(None, pattern=r"^RE\d{4}$")
    date: datetime.date = Field(datetime.date.today())
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    due_date: datetime.date | None = None
    status: str | None = Field(None, pattern="^(sent|paid)$")
    items: list[Item]
    total: float | None = Field(None, ge=0)

    def __init__(self, **data):
        """Initialize the invoice model."""
        super().__init__(**data)

        if not self.items:
            raise ValueError("List of items must not be empty.")

        total = sum([i.price * i.quantity for i in self.items])
        if total == 0:
            raise ValueError("Total must be greater than 0.")
        self.total = total
