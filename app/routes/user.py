from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from core.database import get_db
from app.models import User, Otp, UserData
from core.auth import require_role, get_current_user, create_otp, require_user_profile, require_complete_data
from typing import Annotated
from core.email_utils import successful_upgrade_email_m
from app.schemas import OTPRequest, OTPVerify, ProfileUpdate, PhoneNumberUpdateResponse, OTPRequestResponse, ProfileUpdateResponse, RoleUpdateResponse
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
        
        otp = create_otp()
        
        db.query(Otp).filter(
            Otp.user_id == current_user.user_id,
            Otp.is_active == True
        ).update({"is_active": False})
        
        new_otp = Otp(
            user_id = current_user.user_id,
            otp = otp,
            phone=phone_number,
        )

        sender = send_otp_sms(phone_number=phone_number, otp=otp)
        print(sender)

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


@router.post('/phone-number/verify/')
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

        otp_entry: Otp =  db.query(Otp).filter(Otp.otp == r_otp, Otp.user_id == current_user.user_id, Otp.is_active == True).first()
        
        if not otp_entry:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        if otp_entry.phone != phone:
            raise HTTPException(status_code=400, detail="The phone number is not valid with the related OTP")

        i_otp = otp_entry.otp


        current_timestammp = datetime.now()
        expiry_duration = settings.OTP_EXPIRY_MINUTES
        expiry_timestamp = otp_entry.created_at + timedelta(minutes=expiry_duration)

        print(f'\n current timestamp: {current_timestammp},\n otp-created timestamp: {otp_entry.created_at}\n expiry timestamp{expiry_timestamp}\n')

        if current_timestammp < expiry_timestamp:
            raise HTTPException(status_code=400, detail="OTP is expired")
        
        
        if not str(r_otp) == str(i_otp):
            raise HTTPException(status_code=400, detail="Invalid OTP")
        

        if not current_user.data:
            new_user_data = UserData(
                user_id = current_user.user_id,
                phone = otp_entry.phone
            )

            db.add(new_user_data)
            db.commit()
            db.refresh(new_user_data)
        
        else:
            user_data: UserData = db.query(UserData).filter(UserData.user_id == otp_entry.user_id)
            user_data.phone = phone

            db.commit()

        otp_entry.is_active = False
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


@router.get("/upgrade-to-merchant/", response_model=RoleUpdateResponse)
def upgrade_to_merchant(
    current_user: Annotated[UserData, Depends(require_complete_data())],
    bg_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):

    try:
        if not current_user.user.role == 'buyer':
            raise HTTPException(status_code=403, detail='You are already a merchnat')
        
        current_user.user.role = "merchant"
        db.commit()
        db.refresh(current_user)
        bg_tasks.add_task(successful_upgrade_email_m, current_user.user.email, current_user.user.first_name)

        return {"detail": "You have been upgraded to a merchant"}
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

