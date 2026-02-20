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

    google_score, google_count = collect_google_reviews(hotel)
    booking_score, booking_count = collect_booking_reviews(hotel)
    expedia_score, expedia_count = collect_expedia_reviews(hotel)
    ta_score, ta_count = collect_tripadvisor_reviews(hotel)

    # Track which channels returned live data
    channels = {
        "google": google_score is not None,
        "booking": booking_score is not None,
        "expedia": expedia_score is not None,
        "tripadvisor": ta_score is not None,
    }
    succeeded = [ch for ch, ok in channels.items() if ok]
    failed = [ch for ch, ok in channels.items() if not ok]

    if not succeeded:
        raise HTTPException(
            status_code=502,
            detail=f"All channels failed to collect live data. Check API keys and service availability. Failed: {', '.join(failed)}",
        )

    snapshot = ReviewSnapshot(
        hotel_id=hotel.id,
        source="live",
        google_score=google_score,
        google_count=google_count,
        booking_score=booking_score,
        booking_count=booking_count,
        expedia_score=expedia_score,
        expedia_count=expedia_count,
        tripadvisor_score=ta_score,
        tripadvisor_count=ta_count,
    )

    compute_scores(snapshot)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {
        "snapshot_id": snapshot.id,
        "weighted_average": snapshot.weighted_average,
        "channels_succeeded": succeeded,
        "channels_failed": failed,
    }


@router.post("/groups/{group_id}/collect")
def collect_group_reviews(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = db.query(HotelGroup).filter(HotelGroup.id == group_id, HotelGroup.user_id == user.id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    results = []
    for m in group.memberships:
        hotel = m.hotel

        google_score, google_count = collect_google_reviews(hotel)
        booking_score, booking_count = collect_booking_reviews(hotel)
        expedia_score, expedia_count = collect_expedia_reviews(hotel)
        ta_score, ta_count = collect_tripadvisor_reviews(hotel)

        channels = {
            "google": google_score is not None,
            "booking": booking_score is not None,
            "expedia": expedia_score is not None,
            "tripadvisor": ta_score is not None,
        }
        succeeded = [ch for ch, ok in channels.items() if ok]

        if not succeeded:
            results.append({"hotel_id": hotel.id, "hotel_name": hotel.name, "status": "failed", "channels_succeeded": [], "channels_failed": list(channels.keys())})
            continue

        snapshot = ReviewSnapshot(
            hotel_id=hotel.id,
            source="live",
            google_score=google_score,
            google_count=google_count,
            booking_score=booking_score,
            booking_count=booking_count,
            expedia_score=expedia_score,
            expedia_count=expedia_count,
            tripadvisor_score=ta_score,
            tripadvisor_count=ta_count,
        )
        compute_scores(snapshot)
        db.add(snapshot)
        failed = [ch for ch, ok in channels.items() if not ok]
        results.append({"hotel_id": hotel.id, "hotel_name": hotel.name, "status": "ok", "channels_succeeded": succeeded, "channels_failed": failed})

    db.commit()
    return {"collected": sum(1 for r in results if r["status"] == "ok"), "hotels": results}
