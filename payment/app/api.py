from fastapi import APIRouter, Body, HTTPException, Response, Depends
from .db import get_conn
import psycopg2.extras
from uuid import UUID, uuid4
from .auth import verify_jwt

psycopg2.extras.register_uuid()

router = APIRouter(dependencies=[Depends(verify_jwt)])


@router.get("/api/v1/payments/{paymentUid}")
def payment_by_id(paymentUid: UUID):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT *
            FROM payment
            WHERE payment_uid = %s;
        """, (paymentUid,))
        row = cur.fetchone()

    if not row:
        return {}

    return {
        "status": row["status"],
        "price": row["price"]
    }


@router.post("/api/v1/payments")
def create_payment(price: int = Body(..., embed=True)):
    payment_uid: UUID = uuid4()

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO payment (payment_uid, status, price)
            VALUES (%s, %s, %s)
            """,
            (payment_uid, "PAID", price),
        )
        conn.commit()

    return {
        "paymentUid": payment_uid,
        "status": "PAID",
        "price": price,
    }


@router.patch("/api/v1/payments/{paymentUid}/cancel")
def cancel_payment(paymentUid: UUID):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE payment 
            SET status = 'CANCELED'
            WHERE payment_uid = %s
            """,
            (paymentUid,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        conn.commit()

    return Response(status_code=204)
