import os
from django.shortcuts import render, redirect
from django.contrib.gis.geos import Polygon
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.views.generic import FormView
from .models import LidarFiles
from .forms import MyErrorList, UploadForm
from .rasters import create_rasters, save_as_png, make_z_scatter_plot, make_z_contour_img
from laspy.file import File
from LiDAR_HUB.settings import MEDIA_ROOT


class LidarUploadView(FormView):
    """ Home page of LiDAR HUB. Renders the upload form and
     a custom error message class. """

    form_class = UploadForm
    template_name = 'upload_form.html'
    success_url = '/'

    def get(self, request, *args, **kwargs):
        lidar_data = LidarFiles.objects.order_by('group')
        return render(request, self.template_name, {
            'file_form': self.form_class,
            'lidar_data': lidar_data,
        })

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('file_data')
        srs = request.POST['srs']
        group_name = request.POST['name']
        if form.is_valid():
            read_files(files, srs, group_name)
            return self.form_valid(form)
        else:
            form.error_class = MyErrorList
            lidar_data = LidarFiles.objects.order_by('group')
            return render(request, self.template_name, {
                'file_form': form,
                'lidar_data': lidar_data,
            })


def get_bbox(las_file, srs):
    """ get bounding box coordinates from las file """
    xmin = las_file.header.min[0]
    ymin = las_file.header.min[1]
    xmax = las_file.header.max[0]
    ymax = las_file.header.max[1]
    ct = CoordTransform(SpatialReference(srs), SpatialReference(3857))
    bbox = Polygon.from_bbox((xmin, ymin, xmax, ymax))
    bbox.transform(ct)  # transform to 3857 for leaflet maps
    return bbox


def get_scale(las_file):
    """ get scale factor of XYZ """
    x_scale = las_file.header.scale[0]
    y_scale = las_file.header.scale[1]
    z_scale = las_file.header.scale[2]
    return x_scale, y_scale, z_scale


def set_srs(las_file, srs_choice):
    """ get spatial reference system """
    try:
        srs = las_file.header.srs
    except NotImplementedError:
        srs = SpatialReference(srs_choice)
    return srs


def get_point_count(las_file):
    """ get total number of points in las file """
    points_count = las_file.header.point_records_count
    return points_count


def delete_file(request, lidar_id):
    """ delete lidar record from database """
    lidar_file = LidarFiles.objects.get(pk=lidar_id)
    lidar_file.delete()

    # delete rasters too
    file_name = lidar_file.name.strip('.las')
    for root, dirs, files in os.walk(os.path.join(MEDIA_ROOT, 'rasters')):
        for name in files:
            if file_name in name:
                os.remove(os.path.join(root, name))

    return redirect('main')


def read_files(files, srs, group_name):
    """ Open a .las file and extract information from header block.
    Then add information to a record in the database. """
    for las_file in files:
        las = File(las_file.file.name, mode='r')
        lidar_obj = LidarFiles()
        lidar_obj.name = las_file
        lidar_obj.group = group_name
        lidar_obj.srs = SpatialReference(srs)  # srs saved as user selection TXSP
        lidar_obj.bbox = get_bbox(las, srs)  # srs saved as 3857 for web maps
        lidar_obj.web_srs = lidar_obj.bbox.srid
        lidar_obj.centroid = lidar_obj.bbox.centroid  # srs saved as 3857 for web maps
        lidar_obj.point_count = get_point_count(las)
        lidar_obj.epsg = lidar_obj.srs.srid
        lidar_obj.file_size = float(las_file.size)
        x_scale, y_scale, z_scale = get_scale(las)
        lidar_obj.scale = (x_scale, y_scale, z_scale)
        offsets = get_offset(las)
        lidar_obj.offset = offsets
        mins_maxs = get_min_max(las)
        lidar_obj.min_max_XYZ = mins_maxs
        lidar_obj.version = get_version(las)
        lidar_obj.date_created = get_creation_date(las)
        lidar_obj.las_file = las_file
        lidar_obj.sys_id = get_system_identifier(las)
        lidar_obj.software_id = get_software_id(las)
        lidar_obj.save()
        las.close()
    return


def get_software_id(las):
    """ Get the name of the software that created the file """
    software_id = las.header.software_id
    fixed_str = software_id.rstrip(' \t\r\n\0')
    if fixed_str == '':
        fixed_str = 'UNKNOWN'
    return fixed_str


def get_system_identifier(las):
    """ Get the system identifier """
    sys_id = las.header.system_id
    fixed_str = sys_id.rstrip(' \t\r\n\0')
    if fixed_str == '':
        fixed_str = 'UNKNOWN'
    return fixed_str


def get_creation_date(las):
    """ Get date file was created """
    created = las.header.date
    return created


def get_version(las):
    """ Get the file format version numbers """
    # version = "{0}.{1}".format(las.header.version_major, las.header.version_minor)
    version = las.header.version
    return version


def get_min_max(las):
    """ Get the min and max coordinates """
    xmin = las.header.min[0]
    ymin = las.header.min[1]
    zmin = las.header.min[2]
    xmax = las.header.max[0]
    ymax = las.header.max[1]
    zmax = las.header.max[2]
    return xmin, ymin, zmin, xmax, ymax, zmax


def get_offset(las):
    """
    Offsets.
    It should always be assumed that
    these numbers are used. So to scale a given X from the point record, take the point record X
    multiplied by the X scale factor, and then add the X offset
    """
    offset = las.header.offset
    return offset[0], offset[1], offset[2]


def lidar_map(request):
    """ Loads a leaflet.js map """
    geojson = LidarFiles.to_json(LidarFiles)

    # get jpg info
    return render(request, 'lidar_map.html', {
        'lidar_data': geojson,
    })


def lidar_stats(request, lidar_id):
    """ Loads statistics page for selected file """
    # get file from db
    lidar_file = LidarFiles.objects.get(pk=lidar_id)

    # setup file access
    rstr_name = lidar_file.name.replace('.las', '_intensity.png')
    rstr_file = os.path.join(MEDIA_ROOT, 'rasters', rstr_name)
    tif_name = lidar_file.name.replace('.las', '_intensity.tif')
    tif_file = os.path.join(MEDIA_ROOT, 'rasters', tif_name)
    contour_name = lidar_file.name.replace('.las', '_contour_plot.png')
    contour_file = os.path.join(MEDIA_ROOT, 'rasters', contour_name)
    scatter_name = lidar_file.name.replace('.las', '_scatter_plot.png')
    scatter_file = os.path.join(MEDIA_ROOT, 'rasters', scatter_name)

    # create rasters if they do not already exist
    if not os.path.isfile(rstr_file):
        # open las file
        las = File(lidar_file.las_file.path, mode='r')

        # create raster and stats stuff
        create_rasters(las, tif_file, lidar_file.srs)
        make_z_contour_img(las, contour_file)
        make_z_scatter_plot(las, scatter_file)

        # create png
        save_as_png(tif_file)

        # close las file
        las.close()

    # save django raster_field
    # lidar_file.z_raster = z_raster
    # lidar_file.save()

    # render stats with images of rasters as <img/>
    context = {
        'lidar_file': lidar_file,
        'intensity': rstr_name,
        'scatter': scatter_name,
        'contour': contour_name,
    }
    return render(request, 'stats.html', context=context)
