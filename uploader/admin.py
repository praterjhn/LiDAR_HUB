from django.contrib.gis import admin
from .models import LidarFiles

admin.site.register(LidarFiles, admin.OSMGeoAdmin)
