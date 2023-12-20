from datetime import date

from pydantic import BaseModel


class Person(BaseModel):
    """Person model for the config.toml file."""

    title: str
    image: str
    birthday_place: str


class Social(BaseModel):
    """Social model for the config.toml file."""

    github: str
    linkedin: str


class Education(BaseModel):
    """Education model for the config.toml file."""

    title: str
    start_date: date
    end_date: date | None = None
    institution: str
    location: str
    description: str
    tags: list[str] | None = None


class Experience(BaseModel):
    """Experience model for the config.toml file."""

    title: str
    start_date: date
    end_date: date | None = None
    company: str
    location: str
    description: str
    tags: list[str] | None = None


class Project(BaseModel):
    """Other model for the config.toml file."""

    title: str
    start_date: date
    end_date: date | None = None
    institution: str
    location: str
    description: str
    tags: list[str] | None = None


class CV(BaseModel):
    """Config model for the config.toml file."""

    person: Person
    social: Social
    engagement: str
    skills: list[str]
    education: list[Education]
    experience: list[Experience]
    projects: list[Project]
