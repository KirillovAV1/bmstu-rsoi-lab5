from pika import BlockingConnection, ConnectionParameters, PlainCredentials
from .clients import update_loyalty
import logging
import json
import os
import time

logging.basicConfig(level=logging.INFO)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")

credentials = PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)


def consume_task():
    params = ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )
    while True:
        with BlockingConnection(params) as conn:
            with conn.channel() as ch:
                ch.queue_declare(queue="messages", durable=True)
                ch.basic_consume(queue="messages",
                                 on_message_callback=process_task)
                ch.start_consuming()


def process_task(ch, method, properties, body):
    task = json.loads(body.decode("utf-8"))
    logging.info(f"Получено сообщение: {task}")
    task_type = task.get("type")
    if task_type == "update_loyalty":
        username = task["username"]
        delta = task.get("delta")
        try:
            update_loyalty(username, delta)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            time.sleep(10)
            ch.basic_nack(delivery_tag=method.delivery_tag)


if __name__ == "__main__":
    consume_task()
