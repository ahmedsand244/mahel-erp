from django.urls import path, include
from tenants.views import (
    LandingView,
    RegisterView,
    TenantLoginView,
    TenantLogoutView,
    GoogleLoginView,
    GoogleCallbackView,
    GoogleUnlinkView,
    UserProfileView,
    TenantHomeView,
    SuperAdminView,
)
from dashboard.views import BackupDashboardView

app_name = 'tenants'

urlpatterns = [
    # العامة
    path('',          LandingView.as_view(),      name='landing'),
    path('register/', RegisterView.as_view(),      name='register'),
    path('login/',    TenantLoginView.as_view(),   name='login'),
    path('login/google/', GoogleLoginView.as_view(), name='google_login'),
    path('login/google/callback/', GoogleCallbackView.as_view(), name='google_callback'),
    path('logout/',   TenantLogoutView.as_view(),  name='logout'),

    # الملف الشخصي وإعدادات الحساب وربط Google
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/google/unlink/', GoogleUnlinkView.as_view(), name='google_unlink'),

    # Superadmin
    path('superadmin/', SuperAdminView.as_view(), name='superadmin'),

    # بوابة الـ Tenant — /t/{slug}/
    path('t/<slug:slug>/', TenantHomeView.as_view(), name='tenant_home'),

    # كل روابط النظام تحت /t/{slug}/...
    path('t/<slug:slug>/dashboard/',    include('dashboard.urls')),
    path('t/<slug:slug>/backup/',       BackupDashboardView.as_view(), name='tenant_backup'),
    path('t/<slug:slug>/pos/',          include('pos.urls')),
    path('t/<slug:slug>/inventory/',    include('inventory.urls')),
    path('t/<slug:slug>/maintenance/',  include('maintenance.urls')),
    path('t/<slug:slug>/ledger/',       include('ledger.urls')),
    path('t/<slug:slug>/expenses/',     include('expenses.urls')),
    path('t/<slug:slug>/reports/',      include('reports.urls')),
]
