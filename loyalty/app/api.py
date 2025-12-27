from fastapi import APIRouter, Body, Request, Depends
from .models import LoyaltyInfoResponse
from .db import get_conn
import psycopg2.extras

from .auth import verify_jwt, username_from_claims

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.get("/api/v1/me")
def user_loyalty(request: Request):
    claims = request.state.claims
    print(claims)
    username = username_from_claims(claims)

    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT status, discount, reservation_count as "reservationCount"
            FROM loyalty
            WHERE username = %s;
        """, (username,))
        row = cur.fetchone()
    if not row:
        return {}

    return LoyaltyInfoResponse(**row)


@router.patch("/api/v1/loyalty")
def update_loyalty(
        request: Request,
        delta: int = Body(..., embed=True),
):
    claims = request.state.claims
    username = username_from_claims(claims)

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
        """, (delta, delta, delta, username))

        conn.commit()

    return {"message": "Loyalty обновлена"}
