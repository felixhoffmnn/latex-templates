"""Invoice and line-item data models with VAT calculation."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


class Item(BaseModel):
    """Item model for an invoice file."""

    name: str
    description: str | None = None
    quantity: int = Field(1, ge=1)
    unit: Literal["Stunde", "Stück", "Monat"]
    price: float = Field(0, ge=0)
    total: float = Field(0.0, ge=0)
    vat_rate: Literal[0, 7, 19] | None = None
    vat_amount: float = Field(0.0, ge=0)
    gross_total: float = Field(0.0, ge=0)

    def __init__(self, **data):
        """Initialize the item model."""
        super().__init__(**data)
        self.total = self.price * self.quantity
        effective_rate = self.vat_rate if self.vat_rate is not None else 0
        self.vat_amount = round(self.total * effective_rate / 100, 2)
        self.gross_total = self.total + self.vat_amount


class Invoice(BaseModel):
    """Invoice model for an invoice file."""

    customer_id: int = Field(ge=10000)
    invoice_id: int | None = Field(None, ge=1)
    invoice_number: str | None = Field(None, pattern=r"^RE\d{4,}$")
    date: dt.date = Field(default_factory=dt.date.today)
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    due_date: dt.date | None = None
    status: Literal["draft", "sent", "paid"] = "draft"
    buyer_reference: str | None = None
    items: list[Item]
    total: float = Field(0.0, ge=0)
    total_vat: float = Field(0.0, ge=0)
    total_gross: float = Field(0.0, ge=0)

    def __init__(self, **data):
        """Initialize the invoice model."""
        super().__init__(**data)

        if not self.items:
            raise ValueError("List of items must not be empty.")

        total = sum(i.price * i.quantity for i in self.items)
        if total == 0:
            raise ValueError("Total must be greater than 0.")
        self.total = total
        self.total_vat = round(sum(i.vat_amount for i in self.items), 2)
        self.total_gross = round(self.total + self.total_vat, 2)


class Invoices(BaseModel):
    """Invoices model for an invoice file."""

    invoices: list[Invoice]
