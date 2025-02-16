from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"])
        errors.append({"field": field_path, "message": error["msg"]})

    return JSONResponse(
        status_code=422,
        content={"detail": "Validation Error", "errors": errors},
    )