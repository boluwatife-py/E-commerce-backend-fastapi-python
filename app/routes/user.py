from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from core.database import get_db
from app.models import User
from core.auth import require_role
from typing import Annotated
from core.email_utils import successful_upgrade_email_m

router = APIRouter()

@router.get("/upgrade-to-merchant")
def upgrade_to_merchant(
    current_user: Annotated[User, Depends(require_role(['buyer']))],
    bg_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
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