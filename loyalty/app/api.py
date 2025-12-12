from fastapi import APIRouter, Header, Body
from .models import LoyaltyInfoResponse
from .db import get_conn
import psycopg2.extras

router = APIRouter()


@router.get("/manage/health")
def health():
    return {"status": "ok"}


@router.get("/api/v1/me")
def user_loyalty(x_user_name: str = Header(..., alias="X-User-Name")):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT status, discount, reservation_count as "reservationCount"
            FROM loyalty
            WHERE username = %s;
        """, (x_user_name,))
        row = cur.fetchone()

    if not row:
        return {}

    return LoyaltyInfoResponse(**row)

@router.patch("/api/v1/loyalty")
def update_loyalty(
        x_user_name: str = Header(..., alias="X-User-Name"),
        delta: int = Body(..., embed=True),
):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE loyalty
            SET 
                reservation_count = reservation_count + %s,
                status = CASE
                    WHEN reservation_count + %s < 10 THEN 'BRONZE'
                    WHEN reservation_count + %s < 20 THEN 'SILVER'
                    ELSE 'GOLD'
                END
            WHERE username = %s
            RETURNING reservation_count, status;
        """, (delta, delta, delta, x_user_name))

        conn.commit()

    return {
        "message": "Loyalty обновлена"
    }
