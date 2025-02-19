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