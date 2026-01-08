"""
URL configuration for FAIX Chatbot application.
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Main page
    path('', views.index, name='index'),
    
    # Admin dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # API endpoints
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/feedback/', views.submit_feedback, name='submit_feedback'),
    path('api/conversations/', views.get_conversation_history, name='conversation_history'),
    path('api/admin/dashboard/', views.admin_dashboard_data, name='admin_dashboard_data'),
    path('api/admin/kb/', views.manage_knowledge_base, name='manage_kb'),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

