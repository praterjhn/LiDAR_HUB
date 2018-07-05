from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views
from uploader.views import LidarUploadView

urlpatterns = [
    path('', LidarUploadView.as_view(), name='main'),
    path('map/', views.lidar_map, name='lidar_map'),
    path('stats/<int:lidar_id>', views.lidar_stats, name='stats'),
    path('delete/<int:lidar_id>', views.delete_file, name='delete')
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # for serving rasters; NOTE: remove in production!
