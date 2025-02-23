from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from core.database import get_db
from app.models import User, Order
from core.auth import require_role, get_current_user, create_otp, require_complete_data
from typing import Annotated
from app.schemas import OrderItemResponse, OrderItemBase
from app.crud import get_user_by_phone
from sqlalchemy.ext.asyncio import AsyncSession
from core.message_utils import send_otp_sms
from core.config import settings
from datetime import timedelta, datetime




router = APIRouter(tags=["Orders"])

@router.get('/', response_model=list[OrderItemBase])
def get_user_orders(
    user: Annotated[User, Depends(require_complete_data())],
    db: AsyncSession = Depends(get_db)
):
    try:
        orders: Order = db.query(Order).filter(Order.user_id == user.user_id).all()

        for (order) in orders:
            print(order.order_items)

        return []
    except:
        raise