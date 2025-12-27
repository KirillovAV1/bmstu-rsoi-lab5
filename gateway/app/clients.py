import httpx
import os
import logging
from uuid import UUID
from .circuit_breaker import request_with_circuit_breaker

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gateway")

services = {
    "LOYALTY_URL": os.getenv("LOYALTY_URL", "http://loyalty-microservice:8050"),
    "PAYMENT_URL": os.getenv("PAYMENT_URL", "http://payment-microservice:8060"),
    "RESERVATION_URL": os.getenv("RESERVATION_URL", "http://reservation-microservice:8070"),
}

client = httpx.Client(timeout=5.0)


def _auth_headers(auth: str | None) -> dict:
    return {"Authorization": auth} if auth else {}


def _fetch_hotels_raw(page: int, size: int, auth: str | None) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/hotels"
    log.info(f"GET {url} params={{'page': {page}, 'size': {size}}} headers={{'Authorization': {'set' if auth else 'none'}}}")
    r = client.get(url, params={"page": page, "size": size}, headers=_auth_headers(auth))
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_hotels(page: int, size: int, auth: str | None) -> dict:
    return request_with_circuit_breaker("reservation", _fetch_hotels_raw, page, size, auth)


def _fetch_user_reservations_raw(auth: str | None) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/me"
    log.info(f"GET {url} headers={{'Authorization': {'set' if auth else 'none'}}}")
    r = client.get(url, headers=_auth_headers(auth))
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_user_reservations(auth: str | None) -> dict:
    return request_with_circuit_breaker("reservation", _fetch_user_reservations_raw, auth)


def _fetch_reservation_by_uid_raw(reservation_uid: UUID, auth: str | None) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/reservations/{reservation_uid}"
    log.info(f"GET {url} headers={{'Authorization': {'set' if auth else 'none'}}}")
    r = client.get(url, headers=_auth_headers(auth))
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_reservation_by_uid(reservation_uid: UUID, auth: str | None) -> dict:
    return request_with_circuit_breaker("reservation", _fetch_reservation_by_uid_raw, reservation_uid, auth)


def _fetch_hotel_raw(hotel_uid: UUID, auth: str | None) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/hotel/{hotel_uid}"
    log.info(f"GET {url} headers={{'Authorization': {'set' if auth else 'none'}}}")
    r = client.get(url, headers=_auth_headers(auth))
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_hotel(hotel_uid: UUID, auth: str | None) -> dict:
    return request_with_circuit_breaker("reservation", _fetch_hotel_raw, hotel_uid, auth)


def _create_reservation_in_service_raw(res_data: dict, auth: str | None) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/reservations"
    log.info(f"POST {url} headers={{'Authorization': {'set' if auth else 'none'}}} json={res_data}")
    r = client.post(url, headers=_auth_headers(auth), json=res_data)
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def create_reservation_in_service(res_data: dict, auth: str | None) -> dict:
    return request_with_circuit_breaker("reservation", _create_reservation_in_service_raw, res_data, auth)


def _create_payment_raw(price: int, auth: str | None) -> dict:
    url = f"{services['PAYMENT_URL']}/api/v1/payments"
    log.info(f"POST {url} headers={{'Authorization': {'set' if auth else 'none'}}} json={{'price': {price}}}")
    r = client.post(url, headers=_auth_headers(auth), json={"price": price})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def create_payment(price: int, auth: str | None) -> dict:
    return request_with_circuit_breaker("payment", _create_payment_raw, price, auth)


def _fetch_payment_raw(payment_uid: UUID, auth: str | None) -> dict:
    url = f"{services['PAYMENT_URL']}/api/v1/payments/{payment_uid}"
    log.info(f"GET {url} headers={{'Authorization': {'set' if auth else 'none'}}}")
    r = client.get(url, headers=_auth_headers(auth))
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_payment(payment_uid: UUID, auth: str | None) -> dict:
    return request_with_circuit_breaker("payment", _fetch_payment_raw, payment_uid, auth)


def _fetch_user_loyalty_raw(auth: str | None) -> dict:
    url = f"{services['LOYALTY_URL']}/api/v1/me"
    log.info(f"GET {url} headers={{'Authorization': {'set' if auth else 'none'}}}")
    r = client.get(url, headers=_auth_headers(auth))
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_user_loyalty(auth: str | None) -> dict:
    return request_with_circuit_breaker("loyalty", _fetch_user_loyalty_raw, auth)


def _update_loyalty_raw(auth: str | None, delta: int) -> dict:
    url = f"{services['LOYALTY_URL']}/api/v1/loyalty"
    log.info(f"PATCH {url} headers={{'Authorization': {'set' if auth else 'none'}}} json={{'delta': {delta}}}")
    r = client.patch(url, headers=_auth_headers(auth), json={"delta": delta})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def update_loyalty(auth: str | None, delta: int) -> dict:
    return request_with_circuit_breaker("loyalty", _update_loyalty_raw, auth, delta)


def _cancel_payment_raw(payment_uid: UUID, auth: str | None) -> None:
    url = f"{services['PAYMENT_URL']}/api/v1/payments/{payment_uid}/cancel"
    log.info(f"PATCH {url} headers={{'Authorization': {'set' if auth else 'none'}}}")
    r = client.patch(url, headers=_auth_headers(auth))
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()


def cancel_payment(payment_uid: UUID, auth: str | None) -> None:
    return request_with_circuit_breaker("payment", _cancel_payment_raw, payment_uid, auth)


def _cancel_reservation_raw(reservation_uid: UUID, auth: str | None) -> None:
    url = f"{services['RESERVATION_URL']}/api/v1/reservations/{reservation_uid}/cancel"
    log.info(f"PATCH {url} headers={{'Authorization': {'set' if auth else 'none'}}}")
    r = client.patch(url, headers=_auth_headers(auth))
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()


def cancel_reservation(reservation_uid: UUID, auth: str | None) -> None:
    return request_with_circuit_breaker("reservation", _cancel_reservation_raw, reservation_uid, auth)
