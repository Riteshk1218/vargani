"""File storage in PostgreSQL, for hosting without a persistent disk (Render free plan and similar).

Uploads are small (logos, re-encoded bill photos, report exports), so keeping them in the database is simple
and means database backups include them.
"""

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    def _model(self):
        from .models import StoredFile

        return StoredFile

    def _open(self, name, mode="rb"):
        row = self._model().objects.filter(name=name).only("content").first()
        if row is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(row.content), name=name)

    def _save(self, name, content):
        content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode()
        self._model().objects.create(name=name, content=data, size=len(data))
        return name

    def exists(self, name):
        return self._model().objects.filter(name=name).exists()

    def delete(self, name):
        self._model().objects.filter(name=name).delete()

    def size(self, name):
        row = self._model().objects.filter(name=name).only("size").first()
        if row is None:
            raise FileNotFoundError(name)
        return row.size

    def url(self, name):
        return f"{settings.MEDIA_URL}{name}"
