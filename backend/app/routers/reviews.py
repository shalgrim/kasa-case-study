from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Hotel, HotelGroup, ReviewSnapshot, User
from ..services.collectors.booking import collect_booking_reviews
from ..services.collectors.expedia import collect_expedia_reviews
from ..services.collectors.google import collect_google_reviews
from ..services.collectors.tripadvisor import collect_tripadvisor_reviews
from ..services.scoring import compute_scores

router = APIRouter()


@router.post("/hotels/{hotel_id}/collect")
def collect_hotel_reviews(hotel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")

    # Get latest snapshot as base
    latest = hotel.snapshots[0] if hotel.snapshots else None

    google_score, google_count = collect_google_reviews(hotel)
    booking_score, booking_count = collect_booking_reviews(hotel)
    expedia_score, expedia_count = collect_expedia_reviews(hotel)
    ta_score, ta_count = collect_tripadvisor_reviews(hotel)

    snapshot = ReviewSnapshot(
        hotel_id=hotel.id,
        source="live",
        google_score=google_score if google_score is not None else (latest.google_score if latest else None),
        google_count=google_count if google_count is not None else (latest.google_count if latest else None),
        booking_score=booking_score if booking_score is not None else (latest.booking_score if latest else None),
        booking_count=booking_count if booking_count is not None else (latest.booking_count if latest else None),
        expedia_score=expedia_score if expedia_score is not None else (latest.expedia_score if latest else None),
        expedia_count=expedia_count if expedia_count is not None else (latest.expedia_count if latest else None),
        tripadvisor_score=ta_score if ta_score is not None else (latest.tripadvisor_score if latest else None),
        tripadvisor_count=ta_count if ta_count is not None else (latest.tripadvisor_count if latest else None),
    )

    compute_scores(snapshot)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"snapshot_id": snapshot.id, "weighted_average": snapshot.weighted_average}


@router.post("/groups/{group_id}/collect")
def collect_group_reviews(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(HotelGroup).filter(HotelGroup.id == group_id, HotelGroup.user_id == user.id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    results = []
    for m in group.memberships:
        hotel = m.hotel
        latest = hotel.snapshots[0] if hotel.snapshots else None

        google_score, google_count = collect_google_reviews(hotel)
        booking_score, booking_count = collect_booking_reviews(hotel)
        expedia_score, expedia_count = collect_expedia_reviews(hotel)
        ta_score, ta_count = collect_tripadvisor_reviews(hotel)

        snapshot = ReviewSnapshot(
            hotel_id=hotel.id,
            source="live",
            google_score=google_score if google_score is not None else (latest.google_score if latest else None),
            google_count=google_count if google_count is not None else (latest.google_count if latest else None),
            booking_score=booking_score if booking_score is not None else (latest.booking_score if latest else None),
            booking_count=booking_count if booking_count is not None else (latest.booking_count if latest else None),
            expedia_score=expedia_score if expedia_score is not None else (latest.expedia_score if latest else None),
            expedia_count=expedia_count if expedia_count is not None else (latest.expedia_count if latest else None),
            tripadvisor_score=ta_score if ta_score is not None else (latest.tripadvisor_score if latest else None),
            tripadvisor_count=ta_count if ta_count is not None else (latest.tripadvisor_count if latest else None),
        )
        compute_scores(snapshot)
        db.add(snapshot)
        results.append({"hotel_id": hotel.id, "hotel_name": hotel.name})

    db.commit()
    return {"collected": len(results), "hotels": results}
