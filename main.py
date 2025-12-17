from fastapi import FastAPI

from routers.author_import.router import router as author_import_router
from routers.pull_request_import.router import router as pull_request_import_router

app = FastAPI(title="Author Import API")
app.include_router(author_import_router)
app.include_router(pull_request_import_router)


@app.get("/healthz", tags=["health"])
def healthcheck():
    return {"status": "ok"}
