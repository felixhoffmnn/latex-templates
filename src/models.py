from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator
from pydantic_extra_types.phone_numbers import PhoneNumber


class Address(BaseModel):
    """Address model."""

    street: str
    zip: str | int
    city: str
    country: str | None = Field(None, pattern=r"^(DE|Germany|Deutschland)$")

    def __init__(self, **data):
        super().__init__(**data)
        if isinstance(data.get("zip"), int):
            self.zip = str(data.get("zip")).zfill(5)


class Bank(BaseModel):
    """Bank model containing the bank account information."""

    iban: str = Field(pattern=r"^[A-Z]{2}\d{2}\s(\d{4}\s){4}\d{2}$|^[A-Z]{2}\d{20}$")
    bic: str = Field(pattern=r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")
    bank_name: str

    @field_validator("iban")
    @classmethod
    def normalize_iban(cls, v: str):
        clean_iban = v.replace(" ", "")
        return " ".join([clean_iban[i : i + 4] for i in range(0, len(clean_iban), 4)])


class Style(BaseModel):
    """Style model for the latex template."""

    font_size: int = 11


class Invoice(BaseModel):
    """Invoice model containing tax and payment information."""

    VAT: int
    due_days: int

    @field_validator("VAT")
    @classmethod
    def check_vat(cls, v: int):
        if v not in [0, 7, 19]:
            raise ValueError("VAT must be 0, 7 or 19")
        return v


class Tax(BaseModel):
    """Tax model containing the tax information like the tax number."""

    number: str
    office: str


class Person(BaseModel):
    """Person model for the config.toml file."""

    first_name: str
    last_name: str
    address: Address
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


class Settings(BaseModel):
    """Settings model to configure the template generation."""

    open_pdf_viewer: bool
    open_mail_client: bool


class Config(BaseModel):
    """Config model for the config.toml file."""

    settings: Settings
    person: Person | None = None
    company: Company
    invoice: Invoice
    style: Style = Style()

    # if the company address is not given, use the person address
    def __init__(self, **data):
        if data.get("company", {}).get("name") is None:
            data["company"]["name"] = data.get("person", {}).get("name")
        if data.get("company", {}).get("address") is None:
            data["company"]["address"] = data.get("person", {}).get("address")
        super().__init__(**data)
