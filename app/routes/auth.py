from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from core.database import get_db
from app.crud import get_user_by_email
from app.models import User, PasswordResetToken, VerificationToken
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas import UserCreate, Token, TokenRefreshRequest, UserResponse, RequestVerificationLink, PasswordResetRequest, ResetPasswordRequest
from core.auth import hash_password, verify_password, create_access_token, create_refresh_token, verify_token, create_verification_token, verify_verification_token, create_password_reset_token, oauth2_scheme
from core.email_utils import send_verification_email, send_reset_password_email, successful_verified_email
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from jose import JWTError, ExpiredSignatureError
from typing import Annotated, Optional


router = APIRouter(tags=['Auth'])


responces = {
    422: {
        "description": "Validation Error",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Validation Error",
                    "errors": [
                        {"field": "body.email", "message": "Invalid email format"},
                        {"field": "body.password", "message": "Password must meet security requirements"}
                    ]
                }
            }
        }
    }
}


@router.post("/signup/", response_model=UserResponse, responses=responces)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        if get_user_by_email(db, user.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user.password = hash_password(user.password)
        db_user = User(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            password_hash=user.password
        )

        db.add(db_user)
        db.flush()
        
        verification_token = create_verification_token(user.email)
        token_entry = VerificationToken(
            token=verification_token,
            user_id=db_user.user_id,
            email=user.email
        )
        db.add(token_entry)
        db.flush()

        
        success, message = send_verification_email(user.email, verification_token)
        if not success:
            raise HTTPException(status_code=503, detail=f"Email service error: {message}")

        
        db.commit()
        db.refresh(db_user)

        return UserResponse(email=db_user.email)

    except HTTPException as e:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database constraint violated. User might already exist.")

    except ValidationError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail="Invalid data format")

    except ValueError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unexpected value error")

    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


@router.post("/request-verification-link/")
async def request_new_verification_link(data: RequestVerificationLink, db: AsyncSession = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == data.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_active:
            raise HTTPException(status_code=400, detail="Email is already verified")
        
        
        db.query(VerificationToken).filter(
            VerificationToken.user_id == user.user_id,
            VerificationToken.is_active == True
        ).update({"is_active": False})

        
        new_token = create_verification_token(user.email)
        token_entry = VerificationToken(
            token=new_token,
            user_id=user.user_id,
            email=user.email
        )

        db.add(token_entry)
        db.commit()

        
        try:
            success, message = send_verification_email(user.email, new_token)
            if not success:
                raise HTTPException(status_code=503, detail=f"Email service error: {message}")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=503, detail=f"Email service error: {str(e)}")

        return {"message": "A new verification link has been sent to your email"}

    except HTTPException as e:
        db.rollback()
        raise e

    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


@router.get('/verify-email/')
async def verify_account(token: str, bg_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), ):
    try:
        email = verify_verification_token(token)

        if not email:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        
        token_entry = db.query(VerificationToken).filter(
            VerificationToken.token == token,
            VerificationToken.is_active == True
        ).first()

        if not token_entry:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        user = db.query(User).filter(User.user_id == token_entry.user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_active:
            return {"message": "Email is already verified"}

        bg_tasks.add_task(successful_verified_email, user.email, user.first_name)
        
        # Activate user and disable token
        user.is_active = True
        token_entry.is_active = False

        db.commit()
        db.refresh(user)

        return {"message": "Email successfully verified. You can now log in."}

    except HTTPException as e:
        db.rollback()
        raise e

    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while verifying the account.")


@router.post("/login/", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is not verified yet")

        access_token = create_access_token({"sub": user.email, "role": user.role})
        refresh_token = create_refresh_token({"sub": user.email})

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    
    except HTTPException as e:
        db.rollback()
        raise e

    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


@router.post("/refresh-token/", response_model=Token)
async def refresh_token(token_data: TokenRefreshRequest):
    try:
        payload = verify_token(token_data.refresh_token)
        email: str = payload.get("sub")

        if not email:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        new_access_token = create_access_token({"sub": email})
        return {"access_token": new_access_token, "refresh_token": token_data.refresh_token, "token_type": "bearer"}

    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


async def store_reset_token(db: AsyncSession, token: str, email: str):
    """
    Deactivates any existing reset token and stores a new one.
    """
    # Deactivate any previous reset token
    db.query(PasswordResetToken).filter(PasswordResetToken.email == email).update({"is_used": True})

    # Store the new reset token
    reset_token = PasswordResetToken(token=token, email=email)
    db.add(reset_token)
    db.commit()
    
@router.post("/forgot-password/")
async def forgot_password(
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """
    Allows only unauthenticated users to request a password reset.
    If a valid token is provided in the Authorization header, reject the request.
    Deactivates any previous reset token before generating a new one.
    """

    
    if authorization:
        token = authorization.replace("Bearer ", "")
        try:
            payload = verify_token(token)
            if payload:
                raise HTTPException(
                    status_code=403,
                    detail="You are already logged in. Logout to reset your password."
                )
        except Exception:
            pass

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        reset_token = create_password_reset_token(user.email)
        store_reset_token(db, reset_token, user.email)

    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to generate password reset token")

    
    try:
        success, message = send_reset_password_email(user.email, reset_token)
        if not success:
            raise HTTPException(status_code=503, detail=f"Email service error: {message}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=503, detail=f"Email service error: {str(e)}")

    return {"message": "A password reset link has been sent to your email"}


@router.post("/reset-password/")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        try:
            payload = verify_token(data.token)
            email = payload.get("sub")
            if not email:
                raise HTTPException(status_code=400, detail="Invalid token")
        except ExpiredSignatureError:
            raise HTTPException(status_code=400, detail="Token has expired")
        except JWTError:
            raise HTTPException(status_code=400, detail="Invalid token")

        
        reset_token = db.query(PasswordResetToken).filter_by(token=data.token).with_for_update().first()

        if not reset_token:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        if reset_token.is_used:
            raise HTTPException(status_code=400, detail="This reset token is no longer valid. Please request a new one.")

        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        
        if verify_password(data.new_password, user.password_hash):
            raise HTTPException(status_code=400, detail="New password cannot be the same as the old password")

        
        if len(data.new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

        
        user.password_hash = hash_password(data.new_password)

        
        reset_token.is_used = True

        try:
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=500, detail="Database error while updating password")

        return {"message": "Password reset successfully. You can now log in."}

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {str(e)}")  # Replace with proper logging
        raise HTTPException(status_code=500, detail="An error occurred while resetting the password.")

    
     