from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.core.permissions import HasOrgPermission
from apps.organizations.models import OrganizationMembership

from .models import DeviceToken, Notification
from .serializers import AnnouncementSerializer, DeviceSerializer, DeviceTokenSerializer, NotificationSerializer
from .services import notify


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """My notifications, newest first, from every organization I belong to. Text is in my language."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        qs = Notification.objects.filter(recipient=self.request.user).select_related("organization", "recipient")
        if self.request.query_params.get("unread") in ("1", "true"):
            qs = qs.filter(read_at__isnull=True)
        return qs

    @extend_schema(request=None, responses=NotificationSerializer)
    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_queryset().filter(pk=pk).first()
        if notification is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.status = Notification.Status.READ
            notification.save(update_fields=["read_at", "status", "updated_at"])
        return Response(NotificationSerializer(notification).data)

    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        count = (
            self.get_queryset()
            .filter(read_at__isnull=True)
            .update(read_at=timezone.now(), status=Notification.Status.READ)
        )
        return Response({"marked": count})

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return Response({"unread": Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()})


class AnnouncementView(APIView):
    """Send a message to everyone with access to the active organization."""

    permission_classes = [IsAuthenticated, HasOrgPermission]

    def get_organization_id(self):
        return None

    def get_required_permissions(self):
        return "notifications.send"

    @extend_schema(request=AnnouncementSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = AnnouncementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = request._org_context.organization
        users = [
            m.user
            for m in OrganizationMembership.objects.filter(
                organization=org, status=OrganizationMembership.Status.ACTIVE
            ).select_related("user")
        ]
        rows = notify(users, "announcement", serializer.validated_data, organization=org)
        audit.record(
            request=request,
            organization=org,
            action="announcement",
            entity_type="notifications.announcement",
            after={**serializer.validated_data, "recipients": len(rows)},
        )
        return Response({"sent": len(rows)}, status=status.HTTP_201_CREATED)


class DeviceRegisterView(APIView):
    """The mobile app registers its push token after login (and whenever FCM rotates it)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=DeviceSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        body = DeviceSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        device, created = DeviceToken.objects.update_or_create(
            token=data["token"],
            defaults={
                "user": request.user,
                "platform": data["platform"],
                "app_version": data["app_version"],
                "is_active": True,
                "failure_count": 0,
                "last_seen_at": timezone.now(),
            },
        )
        return Response({"id": str(device.pk)}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DeviceUnregisterView(APIView):
    """Called on logout so the phone stops receiving this user's notifications."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=DeviceTokenSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        body = DeviceTokenSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        removed = DeviceToken.objects.filter(user=request.user, token=body.validated_data["token"]).update(
            is_active=False
        )
        return Response({"removed": removed})
