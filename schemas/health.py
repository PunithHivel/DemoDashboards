from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    status: str
    host: str
    port: str
    database: str
    username: str
