from fastapi import APIRouter, Depends, Header, Body, HTTPException, Response, status
from .clients import *
from .utils import *
from .producer import publish_task

router = APIRouter()


@router.get("/manage/health")
def health():
    return {"gateway": "ok"}


@router.get("/api/v1/hotels",
            response_model=PaginationResponse,
            summary="Получить список отелей")
def get_hotels(params: GetHotelsQuery = Depends()):
    data = handle_service_errors("reservation", fetch_hotels, params.page, params.size)
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
def get_user_info(x_user_name: str = Header(..., alias="X-User-Name")):
    reservations_data = handle_service_errors("reservation", fetch_user_reservations, x_user_name)

    loyalty = handle_service_errors("loyalty", fetch_user_loyalty, x_user_name, fallback=True)
    reservations: list[ReservationResponse] = []

    for reservation in reservations_data.get("reservations", []):
        payment_data = handle_service_errors("payment", fetch_payment, reservation["paymentUid"], fallback=True)
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
def get_user_reservations(x_user_name: str = Header(..., alias="X-User-Name")):
    reservations_data = handle_service_errors("reservation", fetch_user_reservations, x_user_name)

    reservations: list[ReservationResponse] = []

    for reservation in reservations_data.get("reservations", []):
        payment_data = handle_service_errors("payment", fetch_payment, reservation["paymentUid"], fallback=True)
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
def create_reservation(x_user_name: str = Header(..., alias="X-User-Name"), body: CreateReservationRequest = Body(...)):
    hotel_data = handle_service_errors("reservation", fetch_hotel, body.hotelUid)

    try:
        hotel_data = HotelResponse(**hotel_data)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Отель с UID {body.hotelUid} не найден")

    loyalty = handle_service_errors("loyalty", fetch_user_loyalty, x_user_name, fallback=True)
    discount = loyalty["discount"] if loyalty else 0

    price = calculate_price(body.startDate, body.endDate, hotel_data.price, discount)
    payment_data = handle_service_errors("payment", create_payment, price)

    try:
        update_loyalty(x_user_name, delta=1)
    except Exception:
        cancel_payment(payment_data["paymentUid"])
        raise HTTPException(status_code=503, detail="Loyalty Service unavailable")

    reservation_data = create_reservation_in_service({
        "hotelUid": str(body.hotelUid),
        "paymentUid": str(payment_data["paymentUid"]),
        "startDate": body.startDate.isoformat(),
        "endDate": body.endDate.isoformat(),
        "status": payment_data["status"],
    }, x_user_name)

    return CreateReservationResponse(
        reservationUid=reservation_data["reservationUid"],
        hotelUid=body.hotelUid,
        startDate=body.startDate,
        endDate=body.endDate,
        discount=discount,
        status=payment_data["status"],
        payment=PaymentInfo(
            status=payment_data["status"],
            price=payment_data["price"]
        )
    )


@router.get(
    "/api/v1/reservations/{reservationUid}",
    response_model=ReservationResponse,
    summary="Информация по конкретному бронированию")
def get_reservation(
        reservationUid: UUID,
        x_user_name: str = Header(..., alias="X-User-Name")):
    reservation = handle_service_errors("reservation", fetch_reservation_by_uid, reservationUid, x_user_name)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Бронь не найдена")

    payment_data = handle_service_errors("payment", fetch_payment, reservation["paymentUid"], fallback=True)
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
def delete_reservation(reservationUid: UUID, x_user_name: str = Header(..., alias="X-User-Name")):
    reservation = handle_service_errors("reservation", fetch_reservation_by_uid, reservationUid, x_user_name)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Билет не найден")

    handle_service_errors("payment", cancel_payment, reservation["paymentUid"])
    try:
        update_loyalty(x_user_name, delta=-1)
    except Exception:
        publish_task({
            "type": "update_loyalty",
            "username": x_user_name,
            "delta": -1})

    cancel_reservation(reservationUid, x_user_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/loyalty",
            summary="Получить информацию о статусе в программе лояльности")
def get_loyalty_status(x_user_name: str = Header(..., alias="X-User-Name")):
    loyalty = handle_service_errors("loyalty", fetch_user_loyalty, x_user_name)
    return loyalty
