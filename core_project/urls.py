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

import os
from django.http import HttpResponse

def manifest_view(request):
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='application/manifest+json; charset=utf-8')
    return HttpResponse('{}', content_type='application/json')

def service_worker_view(request):
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    if os.path.exists(sw_path):
        with open(sw_path, 'r', encoding='utf-8') as f:
            response = HttpResponse(f.read(), content_type='application/javascript; charset=utf-8')
            response['Service-Worker-Allowed'] = '/'
            return response
    return HttpResponse('', content_type='application/javascript')

urlpatterns = [
    # PWA Endpoints
    path('manifest.json', manifest_view, name='manifest'),
    path('sw.js',         service_worker_view, name='service_worker'),

    # Core Auth & SaaS Root URLs
    path('',            LandingView.as_view(),      name='landing'),
    path('login/',      TenantLoginView.as_view(),  name='login'),
    path('logout/',     TenantLogoutView.as_view(), name='logout'),
    path('register/',   RegisterView.as_view(),     name='register'),
    path('superadmin/', SuperAdminView.as_view(),   name='superadmin'),
    path('admin/',      admin.site.urls),

    # API Endpoints for Mobile App (Flutter)
    path('api/v1/', include('api.urls')),

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

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': os.path.join(settings.BASE_DIR, 'static')}),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
