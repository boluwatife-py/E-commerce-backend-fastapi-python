from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, UserData


def get_user_by_email(db: AsyncSession, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_phone(db: AsyncSession, phone: str):
    return db.query(UserData).filter(UserData.phone == phone).first()

