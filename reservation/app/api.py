from fastapi import APIRouter, Body, Depends, HTTPException, Response, Request
from uuid import uuid4
from .models import *
import psycopg2.extras
from .db import get_conn
from .utils import *
from .auth import verify_jwt, username_from_claims

psycopg2.extras.register_uuid()
router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.get("/api/v1/hotels")
def list_hotels(params: GetHotelsQuery = Depends()):
    if not params.page:
        params.page = 1
    offset = (params.page - 1) * params.size
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS total FROM hotels;")
        total = cur.fetchone()["total"]

        cur.execute(
            """
            SELECT *
            FROM hotels
            ORDER BY id
            LIMIT %s OFFSET %s;
            """,
            (params.size, offset),
        )
        rows = cur.fetchall()

    items = [build_hotel_from_row(r) for r in rows]
    return {"total": total, "items": items}


@router.get("/api/v1/me")
def user_reservations(request: Request):
    claims = request.state.claims
    username = username_from_claims(claims)

    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT reservation.*, hotels.*
            FROM reservation
            JOIN hotels ON reservation.hotel_id = hotels.id
            WHERE reservation.username = %s;
            """,
            (username,),
        )
        rows = cur.fetchall()

    if not rows:
        return {"reservations": []}

    reservations = [build_reservation_from_row(r) for r in rows]
    return {"reservations": reservations}


@router.get("/api/v1/hotel/{hotelUid}")
def get_hotel(hotelUid: UUID):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT *
            FROM hotels
            WHERE hotel_uid = %s;
            """,
            (hotelUid,),
        )
        row = cur.fetchone()

    if not row:
        return {}

    return build_hotel_from_row(row)


@router.post("/api/v1/reservations")
def create_reservation(
        request: Request,
        body: dict = Body(...),
):
    claims = request.state.claims
    username = username_from_claims(claims)

    reservation_uid = uuid4()

    try:
        hotel_uid = UUID(body["hotelUid"])
        payment_uid = UUID(body["paymentUid"])
    except Exception:
        raise HTTPException(status_code=400, detail="Неверный формат UUID")

    start_date = body.get("startDate")
    end_date = body.get("endDate")
    status_value = body.get("status")

    if not (hotel_uid and payment_uid and start_date and end_date and status_value):
        raise HTTPException(
            status_code=400,
            detail="Не хватает обязательных полей для создания бронирования",
        )

    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id FROM hotels WHERE hotel_uid = %s;", (hotel_uid,))
        hotel_row = cur.fetchone()
        if not hotel_row:
            raise HTTPException(status_code=400, detail="Отель не найден")

        cur.execute(
            """
            INSERT INTO reservation
                (reservation_uid, username, payment_uid, hotel_id, status, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING reservation_uid, status, start_date, end_date;
            """,
            (
                reservation_uid,
                username,
                payment_uid,
                hotel_row["id"],
                status_value,
                start_date,
                end_date,
            ),
        )
        row = cur.fetchone()
        conn.commit()

    return build_created_reservation_response(row, hotel_uid, payment_uid)


@router.get("/api/v1/reservations/{reservationUid}")
def get_reservation(
        request: Request,
        reservationUid: UUID,
):
    claims = request.state.claims
    username = username_from_claims(claims)

    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT reservation.*, hotels.*
            FROM reservation
            JOIN hotels ON reservation.hotel_id = hotels.id
            WHERE reservation.reservation_uid = %s;
            """,
            (reservationUid,),
        )
        row = cur.fetchone()

    if not row or row["username"] != username:
        raise HTTPException(status_code=404, detail="Билет не найден")

    return build_reservation_from_row(row)


@router.patch("/api/v1/reservations/{reservationUid}/cancel", status_code=204)
def cancel_reservation(
        request: Request,
        reservationUid: UUID,
):
    claims = request.state.claims
    username = username_from_claims(claims)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            UPDATE reservation
            SET status = 'CANCELED'
            WHERE reservation_uid = %s
              AND username = %s;
        """, (reservationUid, username))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Бронь не найдена")

        conn.commit()

    return Response(status_code=204)
