from fastapi import APIRouter, Depends, Request, HTTPException
from core.database import get_db
from app.models import Category, Currency
from typing import List, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas import CategoryResponse, CurrencyResponse
from app.services.ip import get_country_dial_code
from geoip2.errors import AddressNotFoundError

router = APIRouter()

@router.get("/categories/", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = db.execute(select(Category))
    categories = result.scalars().all()
    return categories


@router.get("/currencies/", response_model=List[CurrencyResponse])
async def get_currencies(db: AsyncSession = Depends(get_db)):
    result = db.execute(select(Currency))
    currencies = result.scalars().all()
    return currencies


@router.get("/user-country/iso/code/")
async def user_country_iso_code(
    request: Request,
) -> str:
    try:
        status, detail = get_country_dial_code(request)
        if not status:
            raise HTTPException(status_code=503, detail='IP filtering error, (%s)'%detail)
        
        return detail
    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred")




