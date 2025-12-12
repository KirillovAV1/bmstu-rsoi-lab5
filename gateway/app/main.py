from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from .api import router


app = FastAPI(title="Gateway API")
app.include_router(router)

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )