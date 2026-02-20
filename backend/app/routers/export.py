import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Hotel, HotelGroup, User

router = APIRouter()

CSV_HEADERS = [
    "Name",
    "City",
    "State",
    "Keys",
    "Kind",
    "Brand",
    "Parent",
    "Google Score",
    "Google Count",
    "Google Normalized",
    "Booking Score",
    "Booking Count",
    "Booking Normalized",
    "Expedia Score",
    "Expedia Count",
    "Expedia Normalized",
    "TripAdvisor Score",
    "TripAdvisor Count",
    "TripAdvisor Normalized",
    "Weighted Average",
]


def _hotel_to_row(hotel):
    latest = hotel.snapshots[0] if hotel.snapshots else None
    return [
        hotel.name,
        hotel.city,
        hotel.state,
        hotel.keys,
        hotel.kind,
        hotel.brand,
        hotel.parent,
        latest.google_score if latest else "",
        latest.google_count if latest else "",
        latest.google_normalized if latest else "",
        latest.booking_score if latest else "",
        latest.booking_count if latest else "",
        latest.booking_normalized if latest else "",
        latest.expedia_score if latest else "",
        latest.expedia_count if latest else "",
        latest.expedia_normalized if latest else "",
        latest.tripadvisor_score if latest else "",
        latest.tripadvisor_count if latest else "",
        latest.tripadvisor_normalized if latest else "",
        latest.weighted_average if latest else "",
    ]


def _make_csv(hotels):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)
    for hotel in hotels:
        writer.writerow(_hotel_to_row(hotel))
    output.seek(0)
    return output


@router.get("/hotels")
def export_hotels(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    hotels = db.query(Hotel).order_by(Hotel.name).all()
    output = _make_csv(hotels)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hotels_export.csv"},
    )


@router.get("/groups/{group_id}")
def export_group(
    group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    group = (
        db.query(HotelGroup)
        .filter(HotelGroup.id == group_id, HotelGroup.user_id == user.id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    hotels = [m.hotel for m in group.memberships]
    output = _make_csv(hotels)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=group_{group_id}_export.csv"
        },
    )
