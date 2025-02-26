from fastapi import APIRouter, Depends, HTTPException, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Product, Cart, Order, OrderItem
from core.auth import get_current_user, require_complete_data
from typing import Annotated, List
from core.database import get_db
from app.schemas import CartCreate, CartResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select


router = APIRouter(tags=["Cart"])


@router.get('/items/', response_model=List[CartResponse])
def get_cart_items(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)):
    try:
        cart_item = db.query(Cart).filter(Cart.user_id == current_user.user_id)
        cart_response = []
        
        for item in cart_item:
            cart_response.append(
                CartResponse.model_validate(item)
            )
        return cart_response
        
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="An error occurred while fetching cart items.")

@router.post('/create/{product_id}/product/', response_model=CartResponse)
def add_item_to_cart(
    data: CartCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)):
    try:
        product_id = data.product_id
        product = db.query(Product).filter(Product.product_id == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")
        
        if product.seller_id == current_user.user_id:
            raise HTTPException(status_code=403, detail="You cant add your product to cart.")
        
        if not data.quantity > 0:
            raise HTTPException(status_code=422, detail="Quantity must be greater than 0.")
        
        if data.quantity > 50:
            raise HTTPException(status_code=422, detail=f"The max quantity request is 50, {data.quantity} was requested.")
        
        if data.quantity > product.stock_quantity:
            raise HTTPException(status_code=422, detail=f"The requested quantity of {data.quantity} is more than the stock quantity of {product.stock_quantity}.")
        
        
        new_cart_item = Cart(
            product_id=product.product_id,
            quantity=data.quantity,
            user_id=current_user.user_id,
        )
        
        db.add(new_cart_item)
        db.commit()
        db.refresh(new_cart_item)
        
        return CartResponse.model_validate(new_cart_item)
        
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="An error occurred while adding product to cart")

@router.put('/product/{cart_id}')
def edit_cart_item(
    current_user: Annotated[User, Depends(get_current_user)],
    cart_id: int,
    db: AsyncSession = Depends(get_db),
    quantity: int = Form(...,),
):
    try:
        cart_item = db.get(Cart, cart_id)
        
        if not cart_item:
            raise HTTPException(status_code=404, detail="Cart item not found")
        
        if not cart_item.user_id == current_user.user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to edit this item")

        product = db.get(Product, cart_item.product_id)
        
        if not product:
            raise HTTPException(status_code=400, detail="Cart product not found")
        
        if not quantity > 0:
            raise HTTPException(status_code=422, detail="Quantity must be greater than 0.")
        
        if quantity > 50:
            raise HTTPException(status_code=422, detail=f"The max quantity request is 50, {quantity} was requested.")
        
        if quantity > product.stock_quantity:
            raise HTTPException(status_code=422, detail=f"The requested quantity of {quantity} is more than the stock quantity of {product.stock_quantity}.")

        cart_item.quantity = quantity
            
        
        db.commit()
        db.refresh(cart_item)
        
        return CartResponse.model_validate(cart_item)
        
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="An error occurred while changing item quantity.")

@router.delete('/product/{cart_id}')
def delete_cart_item(
    current_user: Annotated[User, Depends(get_current_user)],
    cart_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        cart_item = db.get(Cart, cart_id)
        
        if not cart_item:
            raise HTTPException(status_code=404, detail="Cart item not found")
        
        if not cart_item.user_id == current_user.user_id:
            raise HTTPException(status_code=403, detail="You don thave permission to delete this product")
        
        db.delete(cart_item)
        db.commit()
        
        return {'detail': 'Item deleted successfully'}
    
    except HTTPException as http_exc:
        raise http_exc
    
    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="An error occurred while deleting item.")


@router.post('/cart/validate')
def check_cart_status(
    user: Annotated[User, Depends(require_complete_data())],
    db: AsyncSession = Depends(get_db),
):
    try:
        cart_items = db.query(Cart).filter(Cart.user_id == user.user_id).all()

        if not cart_items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart is empty.")

        issues = []

        for cart_item in cart_items:
            product: Product = cart_item.product

            if not product:
                issues.append({
                    "cart_item_id": cart_item.cart_item_id,
                    "issue": "Product has been deleted."
                })
                continue

            if product.stock_quantity < cart_item.quantity:
                issues.append({
                    "cart_item_id": cart_item.cart_item_id,
                    "issue": "Not enough stock available."
                })


        if issues:
            return {
                "status": "Review Needed",
                "issues": issues
            }

        return {
            "status": "Valid",
            "message": "All cart items are valid."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.post("/checkout/")
async def checkout_cart(
    current_user: Annotated[User, Depends(require_complete_data())],
    db: AsyncSession = Depends(get_db),
):
    try:
        cart_items = current_user.cart
        if not cart_items:            raise HTTPException(status_code=400, detail="Cart is empty.")

        cart_ids = [item.cart_id for item in cart_items]

        result = db.execute(
            select(Cart).where(Cart.cart_id.in_(cart_ids), Cart.user_id == current_user.user_id)
        )
        cart_records = result.scalars().all()

        if not cart_records:
            raise HTTPException(status_code=404, detail="No valid cart items found.")

        issues = []
        valid_cart_items = []

        for cart in cart_records:
            product = cart.product  # Relationship from Cart to Product

            if not product:
                issues.append({
                    "cart_item_id": cart.cart_id,
                    "issue": "Product have been removed."
                })
                continue

            if product.stock_quantity < cart.quantity:
                issues.append({
                    "cart_item_id": cart.cart_id,
                    "issue": "Not enough stock available."
                })
                continue

            valid_cart_items.append(cart)

        if issues:
            return {
                "status": "Review Needed",
                "message": "Some items need to be updated before checkout.",
                "issues": issues
            }

        total_price = sum(cart.product.price * cart.quantity for cart in valid_cart_items)

        new_order = Order(
            user_id=current_user.user_id,
            total_amount=total_price,
            order_status="pending",
        )
        db.add(new_order)
        db.flush()

        order_items = []
        for cart in valid_cart_items:
            order_item = OrderItem(
                order_id=new_order.order_id,
                product_id=cart.product_id,
                quantity=cart.quantity,
                unit_price=cart.product.price,
                total_price=cart.product.price * cart.quantity,
            )
            order_items.append(order_item)
            db.add(order_item)

        for cart in valid_cart_items:
            db.delete(cart)

        db.commit()

        return {
            "message": "Order placed successfully. Continue to payment to start shipping.",
            "order_id": new_order.order_id,
            "next": "Payment route at '/payment/paystack/initiate-payment/'"
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail="Unexpected error occurred while processing order.")
