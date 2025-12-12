import time
from collections import deque


class CircuitBreaker:
    def __init__(self, threshold: int = 10, window: float = 60.0, timeout: float = 5.0, half_open_limit: int = 3):
        self.threshold = threshold
        self.window = window
        self.errors = deque()
        self.state = "CLOSED"
        self.timeout = timeout
        self.half_open_limit = half_open_limit
        self.open_status_time = 0.0

        self.half_open_requests = 0
        self.half_open_successes = 0
        self.half_open_failures = 0

    def clear_errors(self):
        current = time.time()
        while self.errors and (current - self.errors[0] > self.window):
            self.errors.popleft()

    def success_request(self):
        self.state = "CLOSED"
        self.errors.clear()

    def failure_request(self):
        current = time.time()
        self.errors.append(current)
        self.clear_errors()

        if len(self.errors) >= self.threshold:
            self.state = "OPEN"
            self.open_status_time = current

    def half_open_status(self):
        self.state = "HALF_OPEN"
        self.half_open_requests = 0
        self.half_open_successes = 0
        self.half_open_failures = 0

    def request_available(self) -> bool:
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            if time.time() - self.open_status_time >= self.timeout:
                self.half_open_status()
                return True
            return False

        if self.state == "HALF_OPEN":
            if self.half_open_requests < self.half_open_limit:
                self.half_open_requests += 1
                return True
            return False

        return False

    def half_open_attempt(self, success: bool):
        if self.state != "HALF_OPEN":
            return None
        if success:
            self.half_open_successes += 1
            if self.half_open_successes == self.half_open_limit:
                self.success_request()
        else:
            self.half_open_failures += 1
            self.state = "OPEN"
            self.open_status_time = time.time()
            self.errors.append(self.open_status_time)


class CircuitBreakerError(Exception):
    def __init__(self, service: str):
        self.service = service
        super().__init__(f"Circuit Breaker: {self.service} is open")


def request_with_circuit_breaker(service: str, func, *args, **kwargs):
    breaker = breakers[service]

    if not breaker.request_available():
        raise CircuitBreakerError(service)

    try:
        result = func(*args, **kwargs)
    except Exception as e:
        if breaker.state == "HALF_OPEN":
            breaker.half_open_attempt(False)
        else:
            breaker.failure_request()
        raise e

    if breaker.state == "HALF_OPEN":
        breaker.half_open_attempt(True)
    else:
        breaker.success_request()

    return result


breakers = {
    "reservation": CircuitBreaker(),
    "payment": CircuitBreaker(),
    "loyalty": CircuitBreaker(),
}