from pydantic import BaseModel, field_validator


class ContestThemeBase(BaseModel):
    theme: str


class ContestThemeInput(ContestThemeBase):
    """Theme is normalized to lowercase on input."""

    @field_validator("theme", mode="before")
    @classmethod
    def theme_to_lower(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class ContestThemeOutput(ContestThemeBase):
    id: int