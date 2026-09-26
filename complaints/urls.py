from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("notifications/", views.notification_center, name="notifications"),
    path("notifications/<int:notification_id>/open/", views.notification_open, name="notification_open"),
    path("notifications/read-all/", views.notifications_mark_all_read, name="notifications_read_all"),
    path("analytics/", views.analytics, name="analytics"),
    path("reports/", views.reports, name="reports"),
    path("reports/print/", views.report_print, name="report_print"),
    path("reports/complaints.csv", views.complaint_csv, name="complaint_csv"),
    path("reports/staff-workload.csv", views.workload_csv, name="workload_csv"),
    path("reports/feedback.csv", views.feedback_csv, name="feedback_csv"),
    path("management/complaints/", views.administrator_queue, name="admin_queue"),
    path("management/complaints/<str:ticket_number>/", views.administrator_detail, name="admin_detail"),
    path("work/", views.staff_queue, name="staff_queue"),
    path("work/<str:ticket_number>/", views.staff_detail, name="staff_detail"),
    path("complaints/", views.complaint_list, name="list"),
    path("complaints/new/", views.complaint_create, name="create"),
    path("complaints/<str:ticket_number>/", views.complaint_detail, name="detail"),
    path("complaints/<str:ticket_number>/feedback/", views.submit_feedback, name="feedback"),
]
