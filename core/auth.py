from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from core.config import settings
from jose import jwt, JWTError
from app.models import User, UserData
from typing import Optional, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
import secrets, time, hashlib, random

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def create_verification_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_verification_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def create_password_reset_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials - Login Session Expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_email: Optional[str] = payload.get("sub")

        if not user_email:
            raise credentials_exception

        
        user = db.query(User).filter(User.email == user_email).first()

        if not user:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(status_code = status.HTTp_401_UNAUTHORIZED, detail="User account is not yet activated", headers={"WWW-Authenticate": "Bearer"})
        return user

    except JWTError:
        raise credentials_exception

def require_role(required_roles: list[str]):
    """Dependency to check if the user has the required role."""
    def role_checker(user: User = Depends(get_current_user)):
        if user.role not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied, {required_roles}-roles is required")
        return user

    return role_checker

def require_user_profile():
    """Dependency to check if the user has a profile."""
    def data_checker(user: User = Depends(get_current_user)):
        if not user.data:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access denied, Add phone number to continue")
        return user
    
    return data_checker

def require_complete_data():
    """Dependency to check if the user profile is completed."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Complete your profile-address data",
        headers={"WWW-Authenticate": "Bearer"},
    )
    def c_data_checker(user: User = Depends(require_user_profile())) -> User:
        user_data: UserData = user.data

        if not user_data:
            raise credentials_exception

        if not user_data.address or not user_data.city or not user_data.state or not user_data.country or not user_data.zip_code:
            raise credentials_exception
        return user
    return c_data_checker

def create_otp():
    otp = secrets.randbelow(1000000)
    otp = str(otp).zfill(6)

    counter = str(int(time.time()))
    hash_value = hashlib.sha256((otp + counter).encode()).hexdigest()
    otp = ''.join(filter(str.isdigit, hash_value))[:6]

    while len(otp) < 6:
        otp += str(random.randint(0, 9))

    return otp

def verify_otp(db_timestamp: time, r_otp: str, i_otp: str) -> bool:
    try:
        current_timestammp = int(time.time())
        expiry_duration = settings.OTP_EXPIRY_MINUTES * 60
        expiry_timestamp = db_timestamp + expiry_duration

        if current_timestammp > expiry_timestamp:
            return False, 'Expired OTP'
        
        if r_otp != i_otp:
            return False, 'Incorrect OTP'
        
        return True, 'Successfully Verified OTP'
    except Exception as e:
        print(e)
        return False, e