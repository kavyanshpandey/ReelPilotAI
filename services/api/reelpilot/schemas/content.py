from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Language = Literal["English", "Hindi", "Hinglish"]
Tone = Literal["Educational", "Conversational", "Energetic", "Storytelling"]


class GeneratedContent(BaseModel):
    hooks: list[str] = Field(min_length=3, max_length=3)
    script_15: str = Field(min_length=20)
    script_30: str = Field(min_length=40)
    script_60: str = Field(min_length=80)
    caption: str = Field(min_length=20)
    cta: str = Field(min_length=5)
    hashtags: list[str] = Field(min_length=3, max_length=12)
    cover_text: str = Field(min_length=3, max_length=80)
    b_roll: list[str] = Field(min_length=2, max_length=8)


class ContentPackCreate(BaseModel):
    language: Language = "Hinglish"
    tone: Tone = "Conversational"


class ContentPackUpdate(BaseModel):
    hooks: list[str] | None = Field(default=None, min_length=3, max_length=3)
    script_15: str | None = Field(default=None, min_length=20)
    script_30: str | None = Field(default=None, min_length=40)
    script_60: str | None = Field(default=None, min_length=80)
    caption: str | None = Field(default=None, min_length=20)
    cta: str | None = Field(default=None, min_length=5)
    hashtags: list[str] | None = Field(default=None, min_length=3, max_length=12)
    cover_text: str | None = Field(default=None, min_length=3, max_length=80)
    b_roll: list[str] | None = Field(default=None, min_length=2, max_length=8)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one content field is required")
        return self


class ContentPackResponse(GeneratedContent):
    id: str
    cluster_id: str
    version: int
    status: str
    provider: str
    model: str
    prompt_version: str
    language: Language
    tone: Tone
    provider_response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime
    updated_at: datetime

