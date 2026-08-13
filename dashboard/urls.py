from django.urls import path
from .views import (
    DashboardView, GlobalSearchView,
    BackupDashboardView, DownloadDatabaseBackupView, DownloadMediaBackupView, RestoreDatabaseBackupView,
    UploadToGoogleDriveBackupView
)

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard_view'),
    path('api/global-search/', GlobalSearchView.as_view(), name='global_search'),
    path('backup/', BackupDashboardView.as_view(), name='backup_manage'),
    path('backup/download-db/', DownloadDatabaseBackupView.as_view(), name='backup_download_db'),
    path('backup/download-media/', DownloadMediaBackupView.as_view(), name='backup_download_media'),
    path('backup/restore/', RestoreDatabaseBackupView.as_view(), name='backup_restore'),
    path('backup/upload-gdrive/', UploadToGoogleDriveBackupView.as_view(), name='backup_upload_gdrive'),
]
