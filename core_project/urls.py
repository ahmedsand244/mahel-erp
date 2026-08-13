from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from tenants.views import (
    LandingView,
    RegisterView,
    TenantLoginView,
    TenantLogoutView,
    SuperAdminView,
)

urlpatterns = [
    # Core Auth & SaaS Root URLs
    path('',            LandingView.as_view(),      name='landing'),
    path('login/',      TenantLoginView.as_view(),  name='login'),
    path('logout/',     TenantLogoutView.as_view(), name='logout'),
    path('register/',   RegisterView.as_view(),     name='register'),
    path('superadmin/', SuperAdminView.as_view(),   name='superadmin'),
    path('admin/',      admin.site.urls),

    # Tenants SaaS routes (/t/{slug}/...)
    path('', include('tenants.urls')),

    # Fallback legacy single-tenant routes
    path('pos/',         include('pos.urls')),
    path('inventory/',   include('inventory.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('ledger/',      include('ledger.urls')),
    path('expenses/',    include('expenses.urls')),
    path('reports/',     include('reports.urls')),
    path('backup/',      include('dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
