from loguru import logger
from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator
from pydantic_extra_types.phone_numbers import PhoneNumber


class Address(BaseModel):
    """Address model."""

    name: str
    extra: str | None = None
    street: str
    zip: str | int
    city: str
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$")

    @field_validator("zip")
    @classmethod
    def normalize_zip(cls, v: str | int) -> str:
        """Ensure zip is a zero-padded 5-digit string."""
        return str(v).zfill(5)


class Bank(BaseModel):
    """Bank model containing the bank account information."""

    iban: str = Field(pattern=r"^[A-Z]{2}\d{2}\s?(\d{4}\s?){4}\d{2}$|^[A-Z]{2}\d{20}$")
    bic: str = Field(pattern=r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")
    name: str

    @field_validator("iban", mode="before")
    @classmethod
    def normalize_iban(cls, v: str):
        """Normalize IBAN by removing spaces first, then formatting in groups of 4."""
        clean_iban = v.replace(" ", "")
        return " ".join([clean_iban[i : i + 4] for i in range(0, len(clean_iban), 4)])


class Invoice(BaseModel):
    """Invoice model containing tax and payment information."""

    default_vat_rate: int = Field(0, alias="VAT")
    vat_exempt: bool = False
    due_days: int

    model_config = {"populate_by_name": True}

    @field_validator("default_vat_rate")
    @classmethod
    def check_vat(cls, v: int):
        if v not in [0, 7, 19]:
            raise ValueError("VAT must be 0, 7 or 19")
        return v

    @model_validator(mode="after")
    def check_vat_exempt(self):
        if self.vat_exempt and self.default_vat_rate > 0:
            logger.warning(
                f"vat_exempt is True but default_vat_rate is {self.default_vat_rate}. Resetting default_vat_rate to 0."
            )
            self.default_vat_rate = 0
        return self


class Tax(BaseModel):
    """Tax model containing the tax information like the tax number."""

    number: str
    office: str
    vat_id: str | None = None


class Sender(BaseModel):
    """Sender model for the config.yml file."""

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
    """Config model for the config.yml file."""

    settings: Settings
    sender: Sender
    invoice: Invoice
