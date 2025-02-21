# from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, APIRouter
# from core.auth import require_role
# from core.database import get_db
# from app.models import User
# from .products import normalize_image_positions
# from typing import Annotated

router = APIRouter(tags=['Admin'])


# @router.post("/products/{product_id}/images/normalize")
# async def normalize_product_images(
#     current_user: Annotated[User, Depends(require_role(['admin']))],
#     product_id: int,
#     db: AsyncSession = Depends(get_db),
# ):
#     await normalize_image_positions(product_id, db)
#     return {"message": f"Positions for product {product_id} normalized"}
