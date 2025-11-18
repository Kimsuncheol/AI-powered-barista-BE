from pydantic import BaseModel


class MenuImageUploadResponse(BaseModel):
    imageUrl: str
