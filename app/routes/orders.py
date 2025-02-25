from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Form
from core.database import get_db
from app.models import User, Order
from core.auth import require_role, get_current_user, create_otp, require_complete_data
from typing import Annotated
from app.schemas import OrderItemResponse, OrderBase, OrderRequest
from app.crud import get_user_by_phone
from sqlalchemy.ext.asyncio import AsyncSession
from core.message_utils import send_otp_sms
from core.config import settings
from datetime import timedelta, datetime




router = APIRouter(tags=["Orders"])


@router.post('/review/{order_id}/order')
def check_order_status(
    user: Annotated[User, Depends(require_complete_data())],
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        order: Order = db.query(Order).filter(Order.order_id == order_id).first()

        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found.')
        
        if order.user_id != user.user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You are not authorized to review this order.')

        issues = []

        for order_item in order.order_items:
            product = order_item.product

            if not product:
                issues.append({
                    "order_item_id": order_item.order_item_id,
                    "issue": "Product has been deleted."
                })
                continue

            if product.stock_quantity < order_item.quantity:
                issues.append({
                    "order_item_id": order_item.order_item_id,
                    "issue": "Not enough stock available."
                })

            if product.price != order_item.unit_price:
                issues.append({
                    "order_item_id": order_item.order_item_id,
                    "issue": f"Price changed from {order_item.unit_price} to {product.price}."
                })

        if issues:
            return {
                "status": "Review Needed",
                "issues": issues
            }

        return {
            "status": "Valid",
            "message": "Order items are valid for processing."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='An unexpected error occurred.')


@router.get('/', response_model=list[OrderBase])
def get_user_orders(
    user: Annotated[User, Depends(require_complete_data())],
    db: AsyncSession = Depends(get_db)
):
    try:
        orders: Order = db.query(Order).filter(Order.user_id == user.user_id).all()
        
        if not orders:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No orders found for this user.')

        order_response = []
        for order in orders:
            order_response.append(OrderBase(
                total_amount=order.total_amount,
                order_status=order.order_status,
                order_payment_status=order.order_payment_status,
                created_at=order.created_at,
                coupon_id=order.coupon_id,
                order_items=[
                    OrderItemResponse(
                        order_item_id=order_item.order_item_id,
                        product_id=order_item.product_id if order_item.product else None,
                        quantity=order_item.quantity,
                        unit_price=order_item.unit_price if order_item.product else None,
                        total_price=order_item.total_price if order_item.product else None,
                        product_name=order_item.product.name if order_item.product else None,
                    ) for order_item in order.order_items
                ]
            ))

        return order_response
    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='An unexpected error occurred.')