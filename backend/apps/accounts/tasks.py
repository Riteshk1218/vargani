from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .sms import get_sms_backend


@shared_task
def deliver_otp(channel: str, destination: str, subject: str, message: str) -> None:
    if channel == "email":
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [destination])
    else:
        get_sms_backend().send(destination, message)


@shared_task
def send_email(subject: str, message: str, to: str) -> None:
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to])
