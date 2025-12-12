from fastapi import HTTPException
from .models import *
from .circuit_breaker import CircuitBreakerError
import logging

logging.basicConfig(level=logging.INFO)


def calculate_price(start_date: date, end_date: date, price_per_night: int, discount_percent: int) -> int:
    nights: int = (end_date - start_date).days
    return price_per_night * nights * (100 - discount_percent) // 100


def fallback_for_service(service_name: str):
    if service_name == "loyalty":
        return {}

    if service_name == "payment":
        return None


def handle_service_errors(service_name: str, func, *args, fallback: bool = False, **kwargs):
    try:
        return func(*args, **kwargs)
    except CircuitBreakerError as e:
        logging.info(e)
        if fallback:
            return fallback_for_service(service_name)

        raise HTTPException(status_code=503, detail=f"{service_name.capitalize()} Service unavailable")

    except HTTPException as e:
        logging.info(e)
        raise

    except Exception as e:
        logging.info(e)
        if fallback:
            return fallback_for_service(service_name)
        raise HTTPException(status_code=503, detail=f"{service_name.capitalize()} Service unavailable")
