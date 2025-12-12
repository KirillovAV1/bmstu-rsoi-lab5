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


def _fetch_hotels_raw(page: int, size: int) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/hotels"
    log.info(f"GET {url} params={{'page': {page}, 'size': {size}}}")
    r = client.get(url, params={"page": page, "size": size})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_hotels(page: int, size: int) -> dict:
    return request_with_circuit_breaker("reservation", _fetch_hotels_raw, page, size)


def _fetch_user_reservations_raw(username: str) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/me"
    log.info(f"GET {url} headers={{'X-User-Name': '{username}'}}")
    r = client.get(url, headers={"X-User-Name": username})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_user_reservations(username: str) -> dict:
    return request_with_circuit_breaker("reservation", _fetch_user_reservations_raw, username)


def _fetch_reservation_by_uid_raw(reservation_uid: UUID, username: str) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/reservations/{reservation_uid}"
    log.info(f"GET {url} headers={{'X-User-Name': '{username}'}}")
    r = client.get(url, headers={"X-User-Name": username})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_reservation_by_uid(reservation_uid: UUID, username: str) -> dict:
    return request_with_circuit_breaker("reservation", _fetch_reservation_by_uid_raw, reservation_uid, username)


def _fetch_hotel_raw(hotel_uid: UUID) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/hotel/{hotel_uid}"
    log.info(f"GET {url}")
    r = client.get(url)
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_hotel(hotel_uid: UUID) -> dict:
    return request_with_circuit_breaker("reservation", _fetch_hotel_raw, hotel_uid)


def _create_reservation_in_service_raw(res_data: dict, username: str) -> dict:
    url = f"{services['RESERVATION_URL']}/api/v1/reservations"
    log.info(f"POST {url} headers={{'X-User-Name': '{username}'}} json={res_data}")
    r = client.post(url, headers={"X-User-Name": username}, json=res_data)
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def create_reservation_in_service(res_data: dict, username: str) -> dict:
    return request_with_circuit_breaker("reservation", _create_reservation_in_service_raw, res_data, username)


def _create_payment_raw(price: int) -> dict:
    url = f"{services['PAYMENT_URL']}/api/v1/payments"
    log.info(f"POST {url} json={{'price': {price}}}")
    r = client.post(url, json={"price": price})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def create_payment(price: int) -> dict:
    return request_with_circuit_breaker("payment", _create_payment_raw, price)


def _fetch_payment_raw(payment_uid: UUID) -> dict:
    url = f"{services['PAYMENT_URL']}/api/v1/payments/{payment_uid}"
    log.info(f"GET {url}")
    r = client.get(url)
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_payment(payment_uid: UUID) -> dict:
    return request_with_circuit_breaker("payment", _fetch_payment_raw, payment_uid)


def _fetch_user_loyalty_raw(username: str) -> dict:
    url = f"{services['LOYALTY_URL']}/api/v1/me"
    log.info(f"GET {url} headers={{'X-User-Name': '{username}'}}")
    r = client.get(url, headers={"X-User-Name": username})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def fetch_user_loyalty(username: str) -> dict:
    return request_with_circuit_breaker("loyalty", _fetch_user_loyalty_raw, username)


def _update_loyalty_raw(username: str, delta: int) -> dict:
    url = f"{services['LOYALTY_URL']}/api/v1/loyalty"
    log.info(f"PATCH {url} headers={{'X-User-Name': '{username}'}} json={{'delta': {delta}}}")
    r = client.patch(url, headers={"X-User-Name": username}, json={"delta": delta})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()
    return r.json()


def update_loyalty(username: str, delta: int) -> dict:
    return request_with_circuit_breaker("loyalty", _update_loyalty_raw, username, delta)


def _cancel_payment_raw(payment_uid: UUID) -> None:
    url = f"{services['PAYMENT_URL']}/api/v1/payments/{payment_uid}/cancel"
    log.info(f"PATCH {url}")
    r = client.patch(url)
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()


def cancel_payment(payment_uid: UUID) -> None:
    return request_with_circuit_breaker("payment", _cancel_payment_raw, payment_uid)


def _cancel_reservation_raw(reservation_uid: UUID, username: str) -> None:
    url = f"{services['RESERVATION_URL']}/api/v1/reservations/{reservation_uid}/cancel"
    log.info(f"PATCH {url} headers={{'X-User-Name': '{username}'}}")
    r = client.patch(url, headers={"X-User-Name": username})
    log.info(f"Response {r.status_code} {url}")
    r.raise_for_status()


def cancel_reservation(reservation_uid: UUID, username: str) -> None:
    return request_with_circuit_breaker("reservation", _cancel_reservation_raw, reservation_uid, username)
