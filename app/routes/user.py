from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from core.database import get_db
from app.models import User, Otp, UserData, Product
from core.auth import get_current_user, create_otp, require_user_profile, require_complete_data, require_role
from typing import Annotated, List
from core.email_utils import successful_upgrade_email_m
from app.schemas import (OTPRequest, OTPVerify, ProfileUpdate, PhoneNumberUpdateResponse, OTPRequestResponse, ProfileUpdateResponse, RoleUpdateResponse, UserDataResponse, ProductResponse, CategoryResponse, ProductImageResponse, CurrencyResponse)
from app.crud import get_user_by_phone
from sqlalchemy.ext.asyncio import AsyncSession
from core.message_utils import send_otp_sms
from core.config import settings
from datetime import timedelta, datetime


router = APIRouter(tags=['User'])


@router.put('/phone-number/change/', summary="Request to change phone number")
@router.post('/phone-number/add/')
async def request_to_add_phone(
    current_user: Annotated[User, Depends(get_current_user)],
    phone_number: OTPRequest,
    db: AsyncSession = Depends(get_db)
) -> OTPRequestResponse:
    """
    Send OTP for a phone to create user data.
    """

    try:
        phone_number = phone_number.phone_number

        if get_user_by_phone(db, phone_number):
            raise HTTPException(status_code=400, detail="Phone already registered")
        
        
        db.query(Otp).filter(
            Otp.user_id == current_user.user_id,
            Otp.is_active == True
        ).update({"is_active": False})
        
        otp = create_otp()
        
        new_otp = Otp(
            user_id = current_user.user_id,
            otp = otp,
            phone=phone_number,
            created_at = datetime.now(),
        )

        # print(otp)
        try:
            send_otp_sms(phone_number=phone_number, otp=otp)
        except Exception:
            raise
        
        db.add(new_otp)
        db.commit()
        db.refresh(new_otp)

        return {"detail": "OTP sent successfully"}
    
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.post('/verify/phone/')
async def verify_phone_otp(
    current_user: Annotated[User, Depends(get_current_user)],
    data: OTPVerify,
    db: AsyncSession = Depends(get_db)
) -> PhoneNumberUpdateResponse:
    """
    Verifies the OTP and saves the user phone number.
    """
    try:
        r_otp = data.otp
        phone = data.phone_number


        otp_entry: Otp = db.query(Otp).filter(Otp.otp == r_otp, Otp.user_id == current_user.user_id, Otp.is_active == True).first()
        
        print(otp_entry)
        if not otp_entry:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        if otp_entry.phone != phone:
            raise HTTPException(status_code=400, detail="The phone number does not match the related OTP")

        i_otp = otp_entry.otp


        current_timestamp = datetime.now()
        expiry_duration = settings.OTP_EXPIRY_MINUTES
        expiry_timestamp = otp_entry.created_at + timedelta(minutes=expiry_duration)

        if current_timestamp > expiry_timestamp:
            raise HTTPException(status_code=400, detail="OTP is expired")

        if str(r_otp) != str(i_otp):
            raise HTTPException(status_code=400, detail="Invalid OTP")

        user_data = db.get(UserData, current_user.user_id)

        if not user_data:
            new_user_data = UserData(user_id=current_user.user_id, phone=otp_entry.phone)
            db.add(new_user_data)
        else:
            user_data.phone = phone

        otp_entry.is_active = False

        db.commit()

        return {'detail': 'Phone number updated successfully'}

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@router.post('/profile/data/', response_model=ProfileUpdateResponse)
def update_profile(
    current_user: Annotated[User, Depends(require_user_profile())],
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db)):
    try:
        user_data_id = current_user.data

        if not user_data_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied, please add your phone number")

        current_user.data.address = data.address,
        current_user.data.city = data.city,
        current_user.data.state = data.state,
        current_user.data.zip_code = data.zip_code,
        current_user.data.country = data.country

        db.commit()
        return {'detail': 'Profile data updated successfully'}

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occured (%s)"%e)

@router.get('/user/profile/data/')
def get_user_profile(
    user: Annotated[User, Depends(get_current_user)]
) -> UserDataResponse:
    try:
        return UserDataResponse(
            first_name = user.first_name,
            last_name = user.last_name,
            email = user.email,
            role = user.role,
            phone = user.data.phone,
            country = user.data.country,
            state = user.data.state,
            city = user.data.city,
            address = user.data.address,
            zip_code = user.data.zip_code,
        )
    except HTTPException:
        raise 

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/upgrade-to-merchant/", response_model=RoleUpdateResponse)
def upgrade_to_merchant(
    current_user: Annotated[UserData, Depends(require_complete_data())],
    bg_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):

    try:
        if not current_user.role == 'buyer':
            raise HTTPException(status_code=403, detail='You are already a merchnat')
        
        current_user.role = "merchant"
        db.commit()
        db.refresh(current_user)
        bg_tasks.add_task(successful_upgrade_email_m, current_user.email, current_user.first_name)

        return {"detail": "You have been upgraded to a merchant"}
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/product/admin/all/", response_model=List[ProductResponse])
def get_all_user_products(
    user: User = Depends(require_role(['merchant'])),
    db: AsyncSession = Depends(get_db)
):
    try:
        products: Product = db.query(Product).filter(Product.seller_id == user.user_id).all()

        if not products:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        
        product_responses = []
        for product in products:
            first_image_url = None
            if product.product_images:
                first_image = min(product.product_images, key=lambda img: img.rank)
                first_image_url = first_image.image_url

            
            category_response = None
            if product.category:
                category_response = CategoryResponse(
                    category_id=product.category.category_id,
                    name=product.category.name
                )

            currency_response = None
            if product.currency:
                currency_response = CurrencyResponse(
                    code=product.currency.code,
                    name=product.currency.name,
                    symbol=product.currency.symbol
                )

            product_responses.append(
                ProductResponse(
                    product_id=product.product_id,
                    name=product.name,
                    description=product.description,
                    price=float(product.price) if product.price else None,
                    stock_quantity=product.stock_quantity,
                    brand=product.brand,
                    status=product.status,
                    seller_id=product.seller_id,
                    created_at=product.created_at,
                    updated_at=product.updated_at,
                    reviews=[],
                    images=[ProductImageResponse(id=0, image_url=first_image_url, rank=0)] if first_image_url else [],
                    category=category_response,
                    currency=currency_response,
                )
            )

        return product_responses
    except HTTPException as http_exc:
        raise http_exc

    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
