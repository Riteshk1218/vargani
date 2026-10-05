from celery import shared_task

from .models import ExportJob
from .services import run


@shared_task(acks_late=True)
def run_export(job_id: str):
    job = ExportJob.objects.filter(pk=job_id, status=ExportJob.Status.PENDING).first()
    if job is not None:
        run(job)
