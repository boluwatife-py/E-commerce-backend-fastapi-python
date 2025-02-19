import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Order
from core.database import get_db
from core.auth import get_current_user
from core.config import settings


router = APIRouter(tags=['Payments'])

@router.post("/paystack/order/{order_id}/initiate-payment/")
async def initiate_payment(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    order = db.get(Order, order_id)
    if not order or order.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != 'pending':
        raise HTTPException(status_code=400, detail="Order is not in pending status")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.paystack.co/transaction/initialize",
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            json={
                "email": current_user.email,
                "amount": int(order.total_amount * 100),
                "callback_url": "https://localhost:8000/payment/paystack/verify-payment"
            }
        )

    data = response.json()

    if not data.get("status"):
        raise HTTPException(status_code=400, detail=f"Paystack Error: {data.get('message')}")

    return {"payment_url": data["data"]["authorization_url"]}


@router.get("/paystack/verify-payment/")
async def verify_payment(reference: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        )

    data = response.json()

    if not data.get("status"):
        raise HTTPException(status_code=400, detail=f"Paystack verification failed: {data.get('message')}")

    order_id = data["data"]["metadata"]["order_id"]
    order = db.get(Order, order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = 'paid'
    db.commit()

    return {"message": "Payment verified successfully", "order_id": order.order_id}

