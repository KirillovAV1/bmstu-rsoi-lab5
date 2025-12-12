from pika import BlockingConnection, ConnectionParameters, PlainCredentials
import json
import os


RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD")

credentials = PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)


def publish_task(task: dict):
    params = ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )
    body = json.dumps(task).encode("utf-8")
    with BlockingConnection(params) as conn:
        with conn.channel() as ch:
            ch.queue_declare(queue="messages", durable=True)
            ch.basic_publish(
                exchange="",
                routing_key="messages",
                body=body
            )