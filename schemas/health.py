from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    status: str
