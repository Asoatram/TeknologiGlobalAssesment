from __future__ import annotations

from app.db.session import SessionLocal
from app.services.reorder_threshold import recalculate_all_reorder_thresholds


def main() -> None:
    with SessionLocal() as session:
        updated = recalculate_all_reorder_thresholds(session)
        session.commit()

    print(f"Reorder threshold recalculation complete: stocks_updated={updated}")


if __name__ == "__main__":
    main()
