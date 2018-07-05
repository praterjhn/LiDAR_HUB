from django.contrib.gis.db import models
import json


class LidarFiles(models.Model):
    name = models.CharField(max_length=250, null=True, blank=True)
    group = models.CharField(max_length=250, null=True, blank=True)
    bbox = models.PolygonField(null=True, blank=True)  # need srid=3857 for leaflet?
    centroid = models.PointField(null=True, blank=True)
    srs = models.CharField(max_length=1000, null=True, blank=True, default='')
    web_srs = models.CharField(max_length=1000, null=True, blank=True, default='')
    epsg = models.IntegerField(null=True, blank=True)
    point_count = models.IntegerField(null=True, blank=True)
    las_file = models.FileField(upload_to='las/', null=True)  # need AWS gateway
    file_size = models.FloatField(null=True, blank=True)
    version = models.CharField(max_length=10, null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    scale = models.CharField(max_length=500, null=True, blank=True)
    offset = models.CharField(max_length=500, null=True, blank=True)
    min_max_XYZ = models.CharField(max_length=500, null=True, blank=True)
    sys_id = models.CharField(max_length=250, null=True, blank=True)
    software_id = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return self.name

    def to_json(self):
        """ Convert database items to json string. Useful
        for leaflet.js maps. """

        lidar_json = []

        for obj in self.objects.all():
            lidar_json.append({
                'name': obj.name,
                'group_name': obj.group,
                'bbox': obj.bbox.geojson,
                'centroid': obj.centroid.geojson,
                'epsg': obj.epsg,
            })

        return json.dumps(lidar_json)


class LidarStats(models.Model):
    name = models.CharField(max_length=250, null=True, blank=True)
    height_raster = models.RasterField()
    pulse_count_raster = models.RasterField()
    returns = models.IntegerField(null=True, blank=True)
    z_range = models.FloatField(null=True, blank=True)
    mean_z = models.FloatField(null=True, blank=True)
    std_dev = models.FloatField(null=True, blank=True)
    x_range = models.FloatField(null=True, blank=True)
    y_range = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name
