from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from core.database import get_db
from app.models import User, Order
from core.auth import require_role, get_current_user, create_otp, require_complete_data
from typing import Annotated
from app.schemas import OrderItemResponse, OrderBase
from app.crud import get_user_by_phone
from sqlalchemy.ext.asyncio import AsyncSession
from core.message_utils import send_otp_sms
from core.config import settings
from datetime import timedelta, datetime




router = APIRouter(tags=["Orders"])

@router.get('/', response_model=list[OrderBase])
def get_user_orders(
    user: Annotated[User, Depends(require_complete_data())],
    db: AsyncSession = Depends(get_db)
):
    try:
        orders: Order = db.query(Order).filter(Order.user_id == user.user_id).all()
        
        order_response = []
        for order in orders:
            order_response.append(OrderBase(
                total_amount=order.total_amount,
                order_status=order.order_status,
                order_payment_status=order.order_payment_status,
                created_at=order.created_at,
                coupon_id=order.coupon_id,
                order_items=[OrderItemResponse(
                    order_item_id = order_item.order_item_id,
                    product_id = order_item.product_id,
                    quantity = order_item.quantity,
                    unit_price = order_item.unit_price,
                    total_price = order_item.total_price)
                for order_item in order.order_items]
            ))

        return order_response
    except:
        raise