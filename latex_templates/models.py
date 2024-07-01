from datetime import date

from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator
from pydantic_extra_types.phone_numbers import PhoneNumber


class Address(BaseModel):
    """Address model."""

    street: str
    zip: str
    city: str
    country: str | None = Field(None, pattern=r"^(DE|Germany|Deutschland)$")


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

    font_size: int | None


class Invoice(BaseModel):
    """Invoice model for the config.toml file."""

    VAT: int
    due_days: int

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

    first_name: str
    last_name: str
    address: Address
    birthday: date
    email: EmailStr


class Company(BaseModel):
    """Company model for the config.toml file."""

    name: str
    name_long: str | None = None
    address: Address
    email: EmailStr
    website: HttpUrl
    phone: PhoneNumber
    tax: Tax
    bank: Bank


class Config(BaseModel):
    """Config model for the config.toml file."""

    person: Person | None = None
    company: Company
    invoice: Invoice
    style: Style | None = None

    # if the conmpany address is not given, use the person address
    def __init__(self, **data):
        if data.get("company", {}).get("name") is None:
            data["company"]["name"] = data.get("person", {}).get("name")
        if data.get("company", {}).get("address") is None:
            data["company"]["address"] = data.get("person", {}).get("address")
        super().__init__(**data)
