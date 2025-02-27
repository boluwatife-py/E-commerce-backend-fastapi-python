import httpx, json
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Order, Product, Payment
from core.database import get_db
from core.auth import get_current_user
from core.config import settings
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.schemas import InitiatePaymentResponse

router = APIRouter(tags=['Payments'])

@router.post("/paystack/order/{order_id}/initiate-payment/", response_model=InitiatePaymentResponse)
async def initiate_payment(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    try:
        query = (
            select(Order)
            .options(selectinload(Order.order_items))
            .filter(Order.order_id == order_id, Order.order_status == 'pending')
        )
        result = db.execute(query)
        order: Order = result.scalars().first()

        if not order or order.user_id != current_user.user_id:
            raise HTTPException(status_code=404, detail="Order not found.")

        if order.order_status != 'pending':
            raise HTTPException(status_code=400, detail="Order is not in pending status.")

        validation_errors = []
        for order_item in order.order_items:
            product_query = select(Product).filter(Product.product_id == order_item.product_id)
            product_result = db.execute(product_query)
            product: Product = product_result.scalars().first()

            if not product:
                validation_errors.append({
                    "order_item_id": order_item.order_item_id,
                    "error": "Product has been deleted."
                })
                continue

            if product.stock_quantity < order_item.quantity:
                validation_errors.append({
                    "order_item_id": order_item.order_item_id,
                    "error": f"Insufficient stock. Only {product.stock_quantity} left."
                })

            if product.price != order_item.unit_price:
                validation_errors.append({
                    "order_item_id": order_item.order_item_id,
                    "error": f"Price has changed from {order_item.unit_price} to {product.price}.",
                    "new_price": product.price
                })

        if validation_errors:
            return {
                "status": "validation_failed",
                "message": "Order requires review before payment.",
                "issues": validation_errors
            }

        # ✅ Async Paystack API call
        with httpx.Client() as client:
            response = client.post(
                "https://api.paystack.co/transaction/initialize",
                headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
                json={
                    "email": current_user.email,
                    "amount": int(order.total_amount * 100),
                    "callback_url": "http://localhost:8000/paystack/verify-payment",
                    "metadata": json.dumps({"order_id": order.order_id})  # ✅ Fixed missing metadata
                }
            )
        data = response.json()
        if not data.get("status"):
            raise HTTPException(status_code=400, detail=f"Paystack Error: {data.get('message')}")

        return {"payment_url": data["data"]["authorization_url"]}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Unexpected error occurred while processing payment.")




@router.get("/paystack/verify-payment/")
async def verify_payment(
    current_user: Annotated[User, Depends(get_current_user)],
    reference: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        if not reference:
            raise HTTPException(status_code=400, detail="Payment reference is missing.")

        # ✅ Step 1: Verify payment with Paystack API
        with httpx.Client() as client:
            response = client.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
            )
        
        data = response.json()
        if not data.get("status"):
            raise HTTPException(status_code=400, detail=f"Paystack Error: {data.get('message')}")

        transaction_data = data.get("data", {})
        metadata = transaction_data.get("metadata", {})

        # ✅ Fix: Convert metadata string to dictionary if necessary
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata format from Paystack.")

        order_id = metadata.get("order_id")
        if not order_id:
            raise HTTPException(status_code=400, detail="Order ID is missing in Paystack metadata.")

        # ✅ Step 2: Fetch the order from the database
        query = select(Order).filter(Order.order_id == order_id, Order.user_id == current_user.user_id)
        result = db.execute(query)
        order: Order = result.scalars().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        # ✅ Step 3: Check if payment was successful
        payment_status = transaction_data.get("status")
        if payment_status != "success":
            raise HTTPException(status_code=400, detail="Payment was not successful.")

        # ✅ Step 4: Save Payment Details in Payments Table
        new_payment = Payment(
            order_id=order.order_id,
            user_id=current_user.user_id,
            amount=order.total_amount,
            payment_method="paystack",
            payment_status="completed",
            transaction_id=transaction_data.get("reference")
        )
        db.add(new_payment)

        # ✅ Step 5: Update Order Payment Status
        order.order_payment_status = "completed"
        order.order_status = "processing"

        db.commit()  # Commit changes to database

        return {
            "message": "Payment verified successfully!",
            "order_id": order.order_id,
            "order_status": order.order_status,
            "transaction_id": transaction_data.get("reference")
        }

    except HTTPException as http_exc:
        raise http_exc  # Re-raise known HTTP errors

    except Exception as e:
        print(f"Error verifying payment: {e}")  # Log for debugging
        raise HTTPException(status_code=500, detail="Unexpected error occurred while verifying payment.")