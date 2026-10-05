from celery import shared_task

from . import reminders


@shared_task
def send_monthly_reminders() -> int:
    return reminders.send_monthly()
