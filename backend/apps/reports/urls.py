from django.urls import path

from .views import (
    DashboardSummaryView,
    ExportDownloadView,
    ExportJobView,
    ReportExportView,
    ReportListView,
    ReportView,
)

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("reports/", ReportListView.as_view(), name="reports"),
    path("reports/<slug:report_type>/", ReportView.as_view(), name="report"),
    path("reports/<slug:report_type>/exports/", ReportExportView.as_view(), name="report-export"),
    path("exports/<uuid:job_id>/", ExportJobView.as_view(), name="export-job"),
    path("exports/<uuid:job_id>/download/", ExportDownloadView.as_view(), name="export-download"),
]
