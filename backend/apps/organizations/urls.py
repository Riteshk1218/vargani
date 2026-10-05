from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("organizations", views.OrganizationViewSet, basename="organization")
router.register("financial-years", views.FinancialYearViewSet, basename="financial-year")
router.register("members", views.MemberViewSet, basename="member")
router.register("invitations", views.InvitationViewSet, basename="invitation")
router.register("roles", views.RoleViewSet, basename="role")
router.register("permissions", views.PermissionViewSet, basename="permission")

urlpatterns = [
    path("invitations/accept/", views.InvitationAcceptView.as_view(), name="invitation-accept"),
    path("invitations/preview/<str:token>/", views.InvitationPreviewView.as_view(), name="invitation-preview"),
    path("me/organizations/", views.MyOrganizationsView.as_view(), name="my-organizations"),
    path("me/organizations/<uuid:org_id>/", views.MyOrganizationDetailView.as_view(), name="my-organization-detail"),
    *router.urls,
]
