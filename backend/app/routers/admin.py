import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Hotel, HotelGroupMembership, ReviewSnapshot, User
from ..services.csv_import import import_csv

router = APIRouter()

CLEAN_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "hotel_rows_to_import.csv")


@router.post("/reset")
def admin_reset(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    deleted_memberships = db.query(HotelGroupMembership).delete()
    deleted_snapshots = db.query(ReviewSnapshot).delete()
    deleted_hotels = db.query(Hotel).delete()
    db.commit()

    imported = 0
    if os.path.exists(CLEAN_CSV_PATH):
        with open(CLEAN_CSV_PATH, "r") as f:
            content = f.read()
        imported = import_csv(content, db)

    return {"deleted_hotels": deleted_hotels, "imported": imported}
