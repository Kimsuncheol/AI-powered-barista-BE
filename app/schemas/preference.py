from typing import List, Optional

from pydantic import BaseModel, Field


class PreferencesOut(BaseModel):
    favorite_drinks: List[int] = Field(default_factory=list)
    default_size: Optional[str] = None
    default_milk_type: Optional[str] = None
    default_sugar_level: Optional[str] = None

    class Config:
        orm_mode = True
