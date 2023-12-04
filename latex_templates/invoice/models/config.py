from pydantic import BaseModel, Field, validator

from latex_templates.invoice.models.shared import Address


class Bank(BaseModel):
    """Bank model for the config.toml file."""

    iban: str = Field(pattern=r"^[A-Z]{2}\d{2}\s(\d{4}\s){4}\d{2}$|^[A-Z]{2}\d{20}$")
    bic: str = Field(pattern=r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")
    bank_name: str

    @validator("iban")
    @classmethod
    def normalize_iban(cls, v: str):
        clean_iban = v.replace(" ", "")
        return " ".join([clean_iban[i : i + 4] for i in range(0, len(clean_iban), 4)])


class Style(BaseModel):
    """Style model for the config.toml file."""

    serif_font: str | None
    sans_font: str | None
    font_size: int | None
    geometry: str | None


class Invoice(BaseModel):
    """Invoice model for the config.toml file."""

    VAT: int
    due_days: int
    style: Style

    @validator("VAT")
    @classmethod
    def check_vat(cls, v: int):
        if v not in [0, 7, 19]:
            raise ValueError("VAT must be 0, 7 or 19")
        return v


class Tax(BaseModel):
    """Tax model for the config.toml file."""

    number: str
    office: str


class Person(BaseModel):
    """Person model for the config.toml file."""

    name: str
    address: Address


class Company(BaseModel):
    """Company model for the config.toml file."""

    name: str
    name_long: str | None = None
    address: Address
    email: str = Field(pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    website: str = Field(pattern=r"^(http(s)?://)?[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    phone: str = Field(pattern=r"^\+?\d{1,3} ?\d{3} ?\d{6,8}$")
    tax: Tax
    bank: Bank


class Config(BaseModel):
    """Config model for the config.toml file."""

    person: Person | None = None
    company: Company
    invoice: Invoice

    # if the conmpany address is not given, use the person address
    def __init__(self, **data):
        if data.get("company", {}).get("name") is None:
            data["company"]["name"] = data.get("person", {}).get("name")
        if data.get("company", {}).get("address") is None:
            data["company"]["address"] = data.get("person", {}).get("address")
        super().__init__(**data)
