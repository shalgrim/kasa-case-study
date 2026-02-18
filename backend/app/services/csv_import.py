import csv
import io

from sqlalchemy.orm import Session

from ..models import Hotel, ReviewSnapshot
from .scoring import compute_scores


def _parse_number(val: str) -> float | None:
    """Parse a number that may have commas, spaces, or be 'n/a'."""
    val = val.strip()
    if not val or val.lower() == "n/a":
        return None
    val = val.replace(",", "")
    try:
        return float(val)
    except ValueError:
        return None


def _parse_int(val: str) -> int | None:
    result = _parse_number(val)
    if result is None:
        return None
    return int(result)


def import_csv(content: str, db: Session) -> int:
    """Import hotels from the reference CSV. Returns count of imported hotels."""
    reader = csv.reader(io.StringIO(content))

    # Skip two header rows
    next(reader)
    next(reader)

    count = 0
    for row in reader:
        if len(row) < 40:
            continue

        name = row[5].strip()
        if not name:
            continue

        # Check for duplicate by name
        existing = db.query(Hotel).filter(Hotel.name == name).first()
        if existing:
            hotel = existing
        else:
            hotel = Hotel(
                name=name,
                city=row[6].strip() or None,
                state=row[7].strip() or None,
                keys=_parse_int(row[8]),
                kind=row[9].strip() or None,
                brand=row[10].strip() or None,
                parent=row[11].strip() or None,
                booking_name=row[37].strip() or None,
                expedia_name=row[38].strip() or None,
                tripadvisor_name=row[39].strip() or None,
            )
            db.add(hotel)
            db.flush()

        google_score = _parse_number(row[16])
        booking_score = _parse_number(row[17])
        expedia_score = _parse_number(row[18])
        tripadvisor_score = _parse_number(row[19])

        google_count = _parse_int(row[22])
        booking_count = _parse_int(row[23])
        expedia_count = _parse_int(row[24])
        tripadvisor_count = _parse_int(row[25])

        snapshot = ReviewSnapshot(
            hotel_id=hotel.id,
            source="csv_import",
            google_score=google_score,
            google_count=google_count,
            booking_score=booking_score,
            booking_count=booking_count,
            expedia_score=expedia_score,
            expedia_count=expedia_count,
            tripadvisor_score=tripadvisor_score,
            tripadvisor_count=tripadvisor_count,
        )
        compute_scores(snapshot)
        db.add(snapshot)
        count += 1

    db.commit()
    return count
