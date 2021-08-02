#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  8 12:56:43 2021

@author: beyza
"""
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d
import json
import requests


def displayRoute(BBox, latitude, longitude, map='map.png', i=0, path='/Users/beyza/Desktop/STAJ/figures/'):
    
    image = plt.imread(map)
    fig, axes = plt.subplots(figsize=(50,50))
    
    axes.plot(longitude, latitude, 'go--', zorder=1, linewidth=5)
    axes.scatter(longitude[0], latitude[0], s=150, color='red', zorder=2) #starting point is illustrated as red
    axes.set_title('Plotting Spatial Data on UK Map')
    axes.set_xlim(BBox[0],BBox[1])
    axes.set_ylim(BBox[2], BBox[3])
    axes.imshow(image, zorder=0, extent = BBox, aspect='equal');
    
    plt.savefig(path + 'trips_'+ str(i) + '.png')


def displayAllRoutes(BBox, latitudes, longitudes, map='map.png', path='/Users/beyza/Desktop/STAJ/figures/'):
    image = plt.imread(map)
    fig, axes = plt.subplots(figsize=(50 ,50))
    
    for i in range(len(longitudes)):
        axes.plot(longitudes[i], latitudes[i], 'go-', zorder=1, linewidth=5)
        axes.scatter(longitudes[i][0], latitudes[i][0], s=150, color='red', zorder=2)
        
    axes.set_title('Plotting Spatial Data on UK Map')
    axes.set_xlim(BBox[0] ,BBox[1])
    axes.set_ylim(BBox[2] ,BBox[3])
    axes.imshow(image, zorder=0, extent = BBox, aspect= 'equal')
    
    plt.savefig(path + 'trips_ALL.png')
                
    

def displayStopPoints(BBox, long_stops, short_stops, map='map.png', path='/Users/beyza/Desktop/STAJ/figures/'):
    
    image = plt.imread(map)
    
    fig, axes = plt.subplots(figsize=(50,50))
    for lat, lon in long_stops:
        axes.scatter(lon, lat, zorder=1, alpha= 0.8, color='blue', s=120)
        
    for lat, lon in short_stops:
        axes.scatter(lon, lat, zorder=1, alpha= 0.8, color='purple', s=120)
        
    axes.set_title('Plotting Spatial Data on UK Map')
    axes.set_xlim(BBox[0],BBox[1])
    axes.set_ylim(BBox[2],BBox[3])
    axes.imshow(image, zorder=0, extent = BBox, aspect= 'equal');
    
    
    plt.savefig(path + '/stop_points.png')



#MAPBOX 

TOKEN = "pk.eyJ1IjoiYmV5emFjZWsiLCJhIjoiY2txZTY4cXlzMjBhcjJwbXZhcWlwbmlpZyJ9.aiT50biRRR54fBfUukidUw"

trip_counter = 0
avg_speeds = []
durations = []
distances = []

def create_route_geojson(route_json, name, shouldWrite=False):
    """Properly formats GeoJson for Mapbox visualization."""
    global avg_speeds
    global durations
    global distances
    
    routes_dict = {
        "type": "Feature",
        "geometry": {
            "type": "LineString"
        },
        "weight_name": "duration",
        "weight": 718.9,
        "duration": 0,
        "distance": 0,
        "properties": {
            "name": ""
        }
    }
    routes_dict['geometry']['coordinates'] = route_json['geometry']['coordinates']
    routes_dict['legs'] = route_json['legs']
    routes_dict['duration'] = route_json['legs'][0]['duration']
    routes_dict['distance'] = route_json['legs'][0]['distance']
    routes_dict['properties']['name'] = name
    
    
    avg_speeds.append((routes_dict['distance']/1000) / (routes_dict['duration']/3600))
    durations.append(routes_dict['duration']/3600)
    distances.append(routes_dict['distance']/1000)
    
    if shouldWrite: 
        with open('dataoutput/' + name + '.json', 'w') as f:
            json.dump(routes_dict,
                      f,
                      sort_keys=True,
                      indent=4,
                      ensure_ascii=False)


def create_walking_route(row):
    """Get route JSON."""
    global trip_counter
    
    
    base_url = 'https://api.mapbox.com/directions/v5/mapbox/driving/'
    url = base_url + str(row['home_longitude']) + \
        ',' + str(row['home_latitude']) + \
        ';' + str(row['dest_longitude']) + \
        ',' + str(row['dest_latitude'])
    params = {
        'geometries': 'geojson',
        'access_token': TOKEN
    }
    req = requests.get(url, params=params)
    route_json = req.json()['routes'][0]
    #print(route_json)
    
    create_route_geojson(route_json, name="Driver07/driver07_trip_" + str(trip_counter), shouldWrite=True)
    trip_counter += 1


#routes_df.apply(create_walking_route, axis=1) 

#data = {"bird_distance":xdeltas, 'bird_duration':tdeltas, 'mapbox_distance' : distances, 'mapbox_duration' : durations}

#stats_df = pandas.DataFrame(data)
#stats_df.to_excel("mapbox_birdflight.xlsx")  
