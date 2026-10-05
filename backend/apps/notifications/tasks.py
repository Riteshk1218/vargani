from celery import shared_task

from .push import send_push_for


@shared_task(acks_late=True)
def deliver_push(notification_ids: list[str]):
    send_push_for(notification_ids)
