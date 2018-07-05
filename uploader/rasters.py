import os
import time
import numpy as np
from osgeo import gdal, osr, ogr  # pip insall pygdal==2.2.2.3!!!!!!!!!!
from LiDAR_HUB.settings import MEDIA_ROOT
from laspy.file import File
from django.contrib.gis.gdal import GDALRaster
from matplotlib.mlab import griddata
import matplotlib.pyplot as plt
from scipy.interpolate import griddata as scipy_grid
# testing modules
from uploader.srs_choices import txsp_central, txsp_south

PIXEL_SIZE = .5


def create_pulse_count_raster(las, tif, srs):
    """Not yet implemented..."""
    return


def create_rasters(las, tif, srs):
    """
    Create images of las file coverage and statistics

    las = an open laspy File
    tif = 'path/to/tif'
    srs = string format of spatial reference
    """
    print("Creating rasters...")
    start_time = time.time()
    # set up the driver in memory
    driver = ogr.GetDriverByName('Memory')

    # create the data source
    data_source = driver.CreateDataSource('in_mem')  # get in_memory driver

    # create the spatial reference
    sr = osr.SpatialReference()
    sr.ImportFromWkt(srs)

    # create the layer
    layer = data_source.CreateLayer('points', sr, ogr.wkbPoint)

    # Add z field
    field1 = ogr.FieldDefn("Class", ogr.OFSTFloat32)
    field2 = ogr.FieldDefn("Intensity", ogr.OFTInteger)
    field3 = ogr.FieldDefn("Return", ogr.OFSTFloat32)
    layer.CreateField(field1)
    layer.CreateField(field2)
    layer.CreateField(field3)

    # process numpy array of las points and add metadata
    las_points = np.vstack((las.x, las.y, las.z,
                            las.raw_classification,
                            las.intensity,
                            las.return_num)).transpose()

    print('\tCreating points layer...')
    for i, pnt in enumerate(las_points):
        print('\tProcessing {0} of {1}'.format(i, len(las_points)))
        # create the feature
        feature = ogr.Feature(layer.GetLayerDefn())
        # set the attributes from the lidar point
        feature.SetField("Class", float(pnt[3]))
        feature.SetField("Intensity", int(pnt[4]))
        feature.SetField("Return", float(pnt[5]))
        # create the wkt for the feature
        wkt = 'POINT ({0} {1} {2})'.format(float(pnt[0]), float(pnt[1]), float(pnt[2]))
        # create the point from the wkt
        point = ogr.CreateGeometryFromWkt(wkt)
        # set the feature geometry using the point
        feature.SetGeometry(point)
        # create the feature in the layer
        layer.CreateFeature(feature)
        # dereference the feature
        feature = None

    xmin, xmax, ymin, ymax = layer.GetExtent()
    x_res = int((xmax - xmin) / PIXEL_SIZE) + 1  # round up and add additional pixel for remainder
    y_res = int((ymax - ymin) / PIXEL_SIZE) + 1  # round up and add additional pixel for remainder

    # create intensity raster file
    # target_ds = gdal.GetDriverByName('GTiff').Create(tif, x_res, y_res, 1, gdal.GDT_Float32)
    target_ds = gdal.GetDriverByName('GTiff').Create(tif, 500, 500, 1, gdal.GDT_Float32)
    target_ds.SetGeoTransform((xmin, PIXEL_SIZE, 0, ymax, 0, -PIXEL_SIZE))
    band = target_ds.GetRasterBand(1)
    band.SetNoDataValue(0)
    # band.FlushCache()

    # write to intensity raster band (single band)
    print('\tCreating Intensity raster...')
    gdal.RasterizeLayer(target_ds, [1], layer, options=["ATTRIBUTE=Intensity"])
    target_ds = None
    band = None

    # # create classification raster source
    # tif3 = tif.replace('.tif', '_class.tif')
    # target_ds = gdal.GetDriverByName('GTiff').Create(tif3, x_res, y_res, 1, gdal.GDT_Float32)
    # target_ds.SetGeoTransform((xmin, PIXEL_SIZE, 0, ymax, 0, -PIXEL_SIZE))
    # band = target_ds.GetRasterBand(1)
    # band.SetNoDataValue(9999)
    # band.FlushCache()
    #
    # # Create classification raster
    # gdal.RasterizeLayer(target_ds, [1], layer, options=["ATTRIBUTE=Class"])
    # target_ds = None
    # band = None

    layer = None
    print("done... took {0}".format(time.time() - start_time))


def save_as_png(tif):
    """
    Save tif as a JPEG with web mercator projection

    tif = 'path/to/tif/file'
    """
    print("Saving jpeg...")
    start_time = time.time()
    # setup jpg access
    jpg = tif.replace('.tif', '.png')

    # define web mercator for web maps
    web_srs = osr.SpatialReference()
    web_srs.ImportFromEPSG(3857)

    # setup options
    translate_options = gdal.TranslateOptions(format='PNG',
                                              outputType=gdal.GDT_Byte,
                                              scaleParams=[''],
                                              # scaleParams=[[0, 4294967296, 0, 255]],
                                              outputSRS=web_srs)

    # convert tif to jpg
    gdal.Translate(destName=jpg, srcDS=tif, options=translate_options)
    print("done... took {0}".format(time.time() - start_time))


def make_z_scatter_plot(las, output_file):
    """make a scatter plot image of points with height as color"""
    print("Making scatter plot...")
    start_time = time.time()
    xArray, yArray, zArray = [las.x, las.y, las.z]
    plt.scatter(xArray, yArray, c=zArray, cmap='RdYlGn_r', alpha=0.75, marker='.')
    plt.axis('off')
    plt.title('Heights of points')
    # plt.xlabel('X coordinates')
    # plt.ylabel('Y coordinates')
    plt.savefig(output_file)
    plt.close()
    del xArray, yArray, zArray
    print("done... took: {0}".format(time.time() - start_time))


def make_z_contour_img(las, output_file):
    """make a contour map"""
    print("Making contour map...")
    start_time = time.time()
    # make arrays
    xArray, yArray, zArray = [las.x, las.y, las.z]

    # setup resolutions
    xmin, ymin, xmax, ymax = [xArray.min(), yArray.min(), xArray.max(), yArray.max()]
    x_res = int((xmax - xmin) / PIXEL_SIZE) + 1  # round up and add additional pixel for remainder
    y_res = int((ymax - ymin) / PIXEL_SIZE) + 1  # round up and add additional pixel for remainder


    # define grid
    xi = np.linspace(np.min(xArray), np.max(xArray), x_res)
    yi = np.linspace(np.min(yArray), np.max(yArray), y_res)

    # mlab grid
    DEM = griddata(xArray, yArray, zArray, xi, yi, interp='linear')

    # make contours
    levels = np.arange(np.min(DEM), np.max(DEM), 6)
    CS = plt.contour(DEM, levels, linewidths=0.2, colors='k')
    plt.clabel(CS, inline=1, fontsize=6)
    plt.imshow(DEM, cmap='RdYlGn_r', origin='lower')
    plt.colorbar()

    # graph it
    plt.title('Height in feet')
    # plt.xlabel('X range in ft.')
    # plt.ylabel('Y range in ft.')
    plt.savefig(output_file, dpi=900)
    plt.close()
    DEM = None
    del xArray, yArray, zArray
    print("done... took: {0}".format(time.time() - start_time))


def test3(xArray, yArray, zArray, x_res, y_res, output_file):
    """test scipy griddata speed"""
    start_time = time.time()
    # define grid
    xi = np.linspace(np.min(xArray), np.max(xArray), x_res)
    yi = np.linspace(np.min(yArray), np.max(yArray), y_res)

    # scipy grid
    XI, YI = np.meshgrid(xi, yi)
    points = np.vstack((xArray, yArray)).transpose()
    DEM = scipy_grid(points, zArray, (XI, YI), method='linear', fill_value=zArray.min())

    # make contours
    levels = np.arange(np.min(DEM), np.max(DEM), 6)
    CS = plt.contour(DEM, levels, linewidths=0.2, colors='k')
    plt.clabel(CS, inline=1, fontsize=6)
    plt.imshow(DEM, cmap='RdYlGn_r', origin='lower')
    plt.colorbar()

    # graph it
    plt.title('Height in feet')
    plt.xlabel('X range in ft.')
    plt.ylabel('Y range in ft.')
    plt.savefig(output_file, dpi=900)
    plt.close()
    DEM = None
    print("test3... took: {0}".format(time.time() - start_time))


def test4(xArray, yArray, zArray, x_res, y_res, tif, srs, originX, originY):
    """ Test numpy arrays to django raster creator """
    start_time = time.time()
    # define grid
    xi = np.linspace(np.min(xArray), np.max(xArray), x_res)
    yi = np.linspace(np.min(yArray), np.max(yArray), y_res)

    # mlab grid
    # DEM = griddata(xArray, yArray, zArray, xi, yi, interp='linear')
    # scipy grid
    XI, YI = np.meshgrid(xi, yi)
    points = np.vstack((xArray, yArray)).transpose()
    DEM = scipy_grid(points, zArray, (XI, YI), method='linear')#, fill_value=zArray.min())

    # create raster with GeoDjango's implementation of rasters; GDALRaster
    GDALRaster({
        'driver': 'GTiff',
        'width': x_res,
        'height': y_res,
        'name': tif,
        'srid': srs,
        'origin': [originX, originY],
        'geotransform': (originX, PIXEL_SIZE, 0, originY, 0, -PIXEL_SIZE),
        'bands': [{'data': DEM}]
    })
    DEM = None
    print("test4... took: {0}".format(time.time() - start_time))


def test5(xArray, yArray, zArray, x_res, y_res, tif, srs, originX, originY):
    """test numpy array to raster with gdal"""
    print("Running test5...")
    start_time = time.time()
    # create the spatial reference
    sr = osr.SpatialReference()
    sr.ImportFromWkt(srs)

    # define grid
    xi = np.linspace(np.min(xArray), np.max(xArray), x_res)
    yi = np.linspace(np.min(yArray), np.max(yArray), y_res)

    # mlab grid (this is basically a tin)
    DEM = griddata(xArray, yArray, zArray, xi, yi, interp='linear')

    # scipy grid
    # XI, YI = np.meshgrid(xi, yi)
    # points = np.vstack((xArray, yArray)).transpose()
    # DEM = scipy_grid(points, zArray, (XI, YI), method='linear', fill_value=zArray.min())

    driver = gdal.GetDriverByName('GTiff')
    outRaster = driver.Create(tif, x_res, y_res, 1, gdal.GDT_Float64)
    outRaster.SetGeoTransform((originX, PIXEL_SIZE, 0, originY, 0, -PIXEL_SIZE))
    outband = outRaster.GetRasterBand(1)
    outband.WriteArray(DEM)
    outRasterSRS = osr.SpatialReference()
    outRasterSRS.ImportFromWkt(srs)
    outRaster.SetProjection(outRasterSRS.ExportToWkt())
    outband.FlushCache()
    DEM = None
    print("test5... took {0}".format(time.time() - start_time))


if __name__ == '__main__':
    """ main program for testing above units (can be run independently from django) """
    # open laspy file
    las = File('/media/sf_share/L437_300FT_ROW_TXSP_S_NAD83_2011_USFT.las', mode='r')

    # file access
    las_file = 'L437_300FT_ROW_TXSP_S_NAD83_2011_USFT.las'
    intensity_tif_name = las_file.replace('.las', '_intensity.tif')
    intensity_tif_file = os.path.join(MEDIA_ROOT, 'rasters', intensity_tif_name)

    # txsp that matches file
    srs = txsp_south  # hard coded to test file

    # test calls
    create_rasters(las, intensity_tif_file, srs)
    save_as_png(intensity_tif_file)

    scatter_plot_file = intensity_tif_file.replace('.tif', '_scatter_plot.png')
    # make_z_scatter_plot(las, scatter_plot_file)

    contour_img_file = scatter_plot_file.replace('scatter_plot.png', 'contour_plot.png')
    # make_z_contour_img(las, contour_img_file)

    # # testing interpolate methods
    # # setup arrays
    # xArray = np.asarray(las.x)
    # yArray = np.asarray(las.y)
    # zArray = np.asarray(las.z)
    #
    # # setup resolutions
    # xmin, ymin, xmax, ymax = [xArray.min(), yArray.min(), xArray.max(), yArray.max()]
    # x_res = int((xmax - xmin) / PIXEL_SIZE) + 1  # round up and add additional pixel for remainder
    # y_res = int((ymax - ymin) / PIXEL_SIZE) + 1  # round up and add additional pixel for remainder

    # test3_output = contour_img_file.replace('2.png', '3.png')
    # test3(xArray, yArray, zArray, x_res, y_res, test3_output)
    #
    # test4_output = test3_output.replace('3.png', '4.tif')
    # test4(xArray, yArray, zArray, x_res, y_res, test4_output, srs, xmin, ymax)  # have to use xmax with txsp coordinates
    #
    # test5_output = test4_output.replace('4.tif', '5.tif')
    # test5(xArray, yArray, zArray, x_res, y_res, test5_output, srs, xmin, ymax)  # have to use xmax with txsp coordinates

    # close laspy file
    las.close()
