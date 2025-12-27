from fastapi import APIRouter, Depends, Body, HTTPException, Response, status, Request
from .clients import *
from .utils import *
from .producer import publish_task
from .auth import verify_jwt, username_from_claims

router = APIRouter(dependencies=[Depends(verify_jwt)])


def _auth(request: Request) -> str | None:
    return request.headers.get("Authorization")


def _username(request: Request) -> str:
    claims = getattr(request.state, "claims", None)
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="Некорректная авторизация")
    return username_from_claims(claims)


@router.get("/api/v1/hotels",
            response_model=PaginationResponse,
            summary="Получить список отелей")
def get_hotels(request: Request, params: GetHotelsQuery = Depends()):
    auth = _auth(request)
    data = handle_service_errors("reservation", fetch_hotels, params.page, params.size, auth)
    items = [HotelResponse(**h) for h in data["items"]]
    return PaginationResponse(
        page=params.page,
        pageSize=params.size,
        totalElements=data["total"],
        items=items,
    )


@router.get(
    "/api/v1/me",
    response_model=UserInfoResponse,
    summary="Информация о пользователе")
def get_user_info(request: Request):
    auth = _auth(request)
    reservations_data = handle_service_errors("reservation", fetch_user_reservations, auth)

    loyalty = handle_service_errors("loyalty", fetch_user_loyalty, auth, fallback=True)
    reservations: list[ReservationResponse] = []

    for reservation in reservations_data.get("reservations", []):
        payment_data = handle_service_errors("payment", fetch_payment, reservation["paymentUid"], auth, fallback=True)
        if payment_data:
            payment = PaymentInfo(
                status=PaymentStatus(payment_data["status"]),
                price=payment_data["price"])
        else:
            payment = payment_data

        reservations.append(
            ReservationResponse(
                reservationUid=reservation["reservationUid"],
                hotel=HotelInfo(**reservation["hotel"]),
                startDate=reservation["startDate"],
                endDate=reservation["endDate"],
                status=reservation["status"],
                payment=payment,
            )
        )

    return UserInfoResponse(
        reservations=reservations,
        loyalty=loyalty
    )


@router.get(
    "/api/v1/reservations",
    response_model=List[ReservationResponse],
    summary="Информация по всем бронированиям пользователя")
def get_user_reservations(request: Request):
    auth = _auth(request)
    reservations_data = handle_service_errors("reservation", fetch_user_reservations, auth)

    reservations: list[ReservationResponse] = []

    for reservation in reservations_data.get("reservations", []):
        payment_data = handle_service_errors("payment", fetch_payment, reservation["paymentUid"], auth, fallback=True)
        if payment_data:
            payment_info = PaymentInfo(
                status=PaymentStatus(payment_data["status"]),
                price=payment_data["price"])
        else:
            payment_info = None

        reservations.append(
            ReservationResponse(
                reservationUid=reservation["reservationUid"],
                hotel=HotelInfo(**reservation["hotel"]),
                startDate=reservation["startDate"],
                endDate=reservation["endDate"],
                status=reservation["status"],
                payment=payment_info,
            )
        )

    return reservations


@router.post("/api/v1/reservations",
             response_model=CreateReservationResponse,
             summary="Забронировать отель")
def create_reservation(request: Request, body: CreateReservationRequest = Body(...)):
    auth = _auth(request)
    username = _username(request)

    hotel_data = handle_service_errors("reservation", fetch_hotel, body.hotelUid, auth)

    try:
        hotel_data = HotelResponse(**hotel_data)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Отель с UID {body.hotelUid} не найден")

    loyalty = handle_service_errors("loyalty", fetch_user_loyalty, auth, fallback=True)
    discount = (loyalty or {}).get("discount", 0)

    price = calculate_price(body.startDate, body.endDate, hotel_data.price, discount)
    payment_data = handle_service_errors("payment", create_payment, price, auth)

    try:
        handle_service_errors("loyalty", update_loyalty, auth, 1)
    except Exception:
        handle_service_errors("payment", cancel_payment, payment_data["paymentUid"], auth)
        raise HTTPException(status_code=503, detail="Loyalty Service unavailable")

    reservation_data = handle_service_errors(
        "reservation",
        create_reservation_in_service,
        {
            "hotelUid": str(body.hotelUid),
            "paymentUid": str(payment_data["paymentUid"]),
            "startDate": body.startDate.isoformat(),
            "endDate": body.endDate.isoformat(),
            "status": "PAID",
        },
        auth
    )

    return CreateReservationResponse(
        reservationUid=reservation_data["reservationUid"],
        hotelUid=body.hotelUid,
        startDate=body.startDate,
        endDate=body.endDate,
        discount=discount,
        status=reservation_data.get("status", "PAID"),
        payment=PaymentInfo(
            status=PaymentStatus(payment_data["status"]),
            price=payment_data["price"]
        )
    )


@router.get(
    "/api/v1/reservations/{reservationUid}",
    response_model=ReservationResponse,
    summary="Информация по конкретному бронированию")
def get_reservation(request: Request, reservationUid: UUID):
    auth = _auth(request)
    reservation = handle_service_errors("reservation", fetch_reservation_by_uid, reservationUid, auth)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Бронь не найдена")

    payment_data = handle_service_errors("payment", fetch_payment, reservation["paymentUid"], auth, fallback=True)
    if payment_data:
        payment = PaymentInfo(
            status=PaymentStatus(payment_data["status"]),
            price=payment_data["price"])
    else:
        payment = payment_data

    return ReservationResponse(
        reservationUid=reservation["reservationUid"],
        hotel=HotelInfo(**reservation["hotel"]),
        startDate=reservation["startDate"],
        endDate=reservation["endDate"],
        status=reservation["status"],
        payment=payment
    )


@router.delete(
    "/api/v1/reservations/{reservationUid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отменить бронирование")
def delete_reservation(request: Request, reservationUid: UUID):
    auth = _auth(request)
    username = _username(request)

    reservation = handle_service_errors("reservation", fetch_reservation_by_uid, reservationUid, auth)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Билет не найден")

    handle_service_errors("payment", cancel_payment, reservation["paymentUid"], auth)
    try:
        handle_service_errors("loyalty", update_loyalty, auth, -1)
    except Exception:
        publish_task({
            "type": "update_loyalty",
            "username": username,
            "delta": -1
        })

    handle_service_errors("reservation", cancel_reservation, reservationUid, auth)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/loyalty",
            summary="Получить информацию о статусе в программе лояльности")
def get_loyalty_status(request: Request):
    auth = _auth(request)
    loyalty = handle_service_errors("loyalty", fetch_user_loyalty, auth, fallback=True)
    return loyalty
