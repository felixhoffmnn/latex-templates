from pydantic import BaseModel, Field, validator


class Company(BaseModel):
    """Company model for the config.toml file."""

    name: str
    name_long: str
    email: str = Field(pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    website: str = Field(pattern=r"^(http(s)?://)?[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    phone: str = Field(pattern=r"^\+?\d{1,3} ?\d{3} ?\d{6,8}$")
    tax_number: str
    tax_office: str


class Address(BaseModel):
    """Address model for the config.toml file."""

    street: str
    zip: str
    city: str
    country: str = Field(pattern=r"^(DE|Germany|Deutschland)$")


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


class Style(BaseModel):
    """Style model for the config.toml file."""

    serif_font: str | None
    sans_font: str | None
    font_size: int | None
    geometry: str | None


class Config(BaseModel):
    """Config model for the config.toml file."""

    company: Company
    address: Address
    bank: Bank
    invoice: Invoice
    style: Style
