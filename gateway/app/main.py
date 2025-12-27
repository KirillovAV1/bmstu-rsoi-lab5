from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from .api import router
from .auth import router as authorize_router

app = FastAPI(title="Gateway API")

app.include_router(authorize_router)
app.include_router(router)

@app.get("/manage/health")
def health():
    return {"gateway": "ok"}

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )