from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from core.database import get_db
from app.models import User, Otp, UserData
from core.auth import require_role, get_current_user, create_otp
from typing import Annotated
from core.email_utils import successful_upgrade_email_m
from app.schemas import OTPRequest, OTPVerify
from app.crud import get_user_by_phone
from sqlalchemy.ext.asyncio import AsyncSession
from core.message_utils import send_otp_sms
from core.config import settings
import time


router = APIRouter()


@router.get("/upgrade-to-merchant")
def upgrade_to_merchant(
    current_user: Annotated[User, Depends(require_role(['buyer']))],
    bg_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):

    try:
        current_user.role = "merchant"
        db.commit()
        db.refresh(current_user)
        bg_tasks.add_task(successful_upgrade_email_m, current_user.email, current_user.first_name)
        return {"message": "You have been upgraded to a merchant"}
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.post('/request-otp/data/phone/')
async def send_otp(
    current_user: Annotated[User, Depends(get_current_user)],
    phone_number: OTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send OTP for a phone to create user data.
    """

    try:
        phone_number = phone_number.phone_number
        if get_user_by_phone(db, phone_number):
            raise HTTPException(status_code=400, detail="Phone already registered")
        
        otp = create_otp()
        
        db.query(Otp).filter(
            Otp.user_id == current_user.user_id,
            Otp.is_active == True
        ).update({"is_active": False})
        
        new_otp = Otp(
            user_id = current_user.user_id,
            otp = otp
        )

        await send_otp_sms(phone_number=phone_number, otp=otp)

        db.add(new_otp)
        db.commit()
        db.refresh(new_otp)

        return {"detail": "OTP sent successfully"}
    
    except HTTPException:
        raise

    except Exception as e:
        print(e)
        db.rollback()
        raise HTTPException(status_code=500, detail="An unexpected error occurred, %s"%e)


@router.post('/verify-otp/data/phone/')
async def verify_otp(
    current_user: Annotated[User, Depends(get_current_user)],
    data: OTPVerify,
    db: AsyncSession = Depends(get_db)
):
    """
    Verifies the OTP and saves the user phone number.
    """

    try:
        r_otp = data.otp
        phone = data.phone_number

        otp_entry = db.query(Otp).filter(
            Otp.otp == r_otp,
            Otp.user_id == current_user.user_id,
            Otp.is_active == True
        ).first()

        if not otp_entry:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        if otp_entry.phone != phone:
            raise HTTPException(status_code=400, detail="The phone number is not valid with the related OTP")

        current_timestammp = int(time.time())
        expiry_duration = settings.OTP_EXPIRY_MINUTES * 60
        expiry_timestamp = otp_entry.created_at + expiry_duration

        if current_timestammp > expiry_timestamp:
            raise HTTPException(status_code=400, detail="OTP is expired")
        
        if r_otp != otp_entry.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        

        new_user_data = UserData(
            phone = otp_entry.phone
        )

        otp_entry.is_active = False

        db.add(new_user_data)
        db.commit()
        db.refresh(new_user_data)
    
    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")