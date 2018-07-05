function make_lidar_map(map_id, lidar_data) {
    var map = L.map(map_id).setView([31.9886, -99.9018], 6);

    L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
        maxZoom: 18,
        id: 'mapbox.streets',
        accessToken: 'pk.eyJ1IjoianByYXRlciIsImEiOiJjajVkZ2hlencwOHF0MzJvZTZocjgyMHpzIn0.RLSAfETdAFhjZES82CHx2Q'
    }).addTo(map);

    L.control.scale({imperial: true}).addTo(map);

    L.easyButton('fas fa-home', function () {
        window.location.href = '/';
    }).addTo(map);

    L.easyButton('fas fa-globe', function (btn, map) {
        map.flyTo([31.9886, -99.9018], 6);
    }).addTo(map);

    var layers = []; // Array of bounding boxes and centroids of each file
    var overlays = {}; // Json of each group of layers

    for (var i = 0; i < lidar_data.length; i++){

        if (i === 0){
            var current_group = lidar_data[i].group_name;
        }

        // attempt to group layers by group_name
        // TODO: Refactor this. It's ugly...
        if (lidar_data[i].group_name !== current_group){
            overlays[current_group] = L.featureGroup(layers);
            overlays[current_group].addTo(map);
            current_group = lidar_data[i].group_name;
            layers = [];
            var bound_box = L.geoJSON(JSON.parse(lidar_data[i].bbox));
            layers.push(bound_box);
            var bound_box_center = JSON.parse(lidar_data[i].centroid);
            var feature_name = lidar_data[i].name;
            layers.push(L.geoJSON(bound_box_center).bindPopup(feature_name));
            if (i === lidar_data.length-1){
                overlays[current_group] = L.featureGroup(layers);
                overlays[current_group].addTo(map);
            }
        }
        else {
            bound_box = L.geoJSON(JSON.parse(lidar_data[i].bbox));
            layers.push(bound_box);
            bound_box_center = JSON.parse(lidar_data[i].centroid);
            feature_name = lidar_data[i].name;
            layers.push(L.geoJSON(bound_box_center).bindPopup(feature_name));
            if (i === lidar_data.length-1){
                overlays[current_group] = L.layerGroup(layers);
                overlays[current_group].addTo(map);
            }
        }
        // var raster_url = "/media/rasters/".concat(feature_name.replace('.las', '.jpg'));
        // var raster_extent = lidar_data.z_raster.extent;
        // var raster_image =  L.imageOverlay(raster_url, bound_box.getBounds());
        // raster_image.addTo(map);
    }
    if (lidar_data.length !== 0) {
        // null = no basemaps
        L.control.layers(null, overlays, {collapsed:false, position:'topleft'}).addTo(map);
    }
}
