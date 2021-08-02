import pandas
import numpy as np
from math import sin, cos, sqrt, atan2, radians, sqrt
from datetime import datetime, timedelta
from visualizer import *
from utils import *
import csv

MIN_TRIP_LENGTH = 3
MAX_TRIP_INTERVAL = 5
FIGURES_DIR = '/Users/beyza/Desktop/STAJ/figures19/'

# Read CSV
df = pandas.read_csv('wo_date_weekday/Driver19.csv')

# Preprocess the dataframe
clean_df = df.drop(0)
clean_df['Longitude'] = clean_df['Longitude'].astype(float)
clean_df['Latitude'] = clean_df['Latitude'].astype(float)
clean_df['Day Index'] = clean_df['Day Index'].astype(int)

# Order the dataframe by "Day Index" and "Time" in ascending order
clean_df['Time'] = pandas.to_datetime(clean_df['Time'], format='%H:%M:%S').dt.time
ordered_df = clean_df.sort_values(by=['Day Index', 'Time'], ascending=True, inplace=False)
ordered_df.reset_index(drop=True, inplace=True)

# Find trips
prevDayIndex = None
prevTime = None
prevIndex = None
prevRow = None

tripStartIndex = None
trips = []

for index, row in ordered_df.iterrows():

    if prevTime is None:  # read the first data
        prevDayIndex = row['Day Index']
        tripStartIndex = index

    elif prevDayIndex != row['Day Index']:  # new day has started
        if prevIndex - tripStartIndex > MIN_TRIP_LENGTH:  # minimum 4 significant points
            trips.append((tripStartIndex, prevIndex))  # add this trip

        prevDayIndex = row['Day Index']
        tripStartIndex = index

    else:  # same day
        # find the time diff between the previous and the current data point
        FMT = '%H:%M:%S'
        tdelta = datetime.strptime(str(row['Time']), FMT) - datetime.strptime(str(prevTime), FMT)
        # print(tdelta, tdelta.seconds)

        if tdelta.seconds >= MAX_TRIP_INTERVAL * 60:
            # time difference >= 5 minutes
            if prevIndex - tripStartIndex > MIN_TRIP_LENGTH:  # minimum 4 significant points
                trips.append((tripStartIndex, prevIndex))  # add this trip
            tripStartIndex = index

        else:  # stayed in the same coordinate
            if prevRow['Latitude'] == row['Latitude'] and prevRow['Longitude'] == row['Longitude']:
                prevRow = row
                continue

    prevTime = row['Time']
    prevIndex = index
    prevRow = row

print('Total number of trips of driver18 in 56 days are:',len(trips))

bboxes = []
latitudes = []
longitudes = []
for start,end in trips:
    # create bbox for each trip
    """
    bbox = (ordered_df[start:end+1]['Longitude'].min(), ordered_df[start:end+1]['Longitude'].max(), 
            ordered_df[start:end+1]['Latitude'].min(), ordered_df[start:end+1]['Latitude'].max())
    bboxes.append(bbox)
    """
    # longitudes and latitudes are kept as array 
    latitudes.append(np.array(ordered_df[start:end+1]['Latitude']))
    longitudes.append(np.array(ordered_df[start:end+1]['Longitude']))

# big map
bbox = (ordered_df['Longitude'].min(), ordered_df['Longitude'].max(),
            ordered_df['Latitude'].min(), ordered_df['Latitude'].max())
bboxes.append(bbox)



"""
print("Display routes!!!")
for i in range(len(trips)):
    # displayRoute(bboxes[-1], latitudes[i], longitudes[i], map='map.png', i=i, path=FIGURES_DIR)
    displayAllRoutes(bboxes[-1], latitudes, longitudes, map='map.png', path=FIGURES_DIR)
"""

# STATISTICS
FMT = '%H:%M:%S'
current_trip = 0  # which index in the trip array
distance_dict = {}  # 1: [distances], 2: [distances]
duration_dict = {}  # 1: [duration], 2: [duration]

for start, end in trips:  # walking through all trips

    # find the trip day index 
    day_index = np.array(ordered_df[start:start + 1]['Day Index'])[0]

    # find trip time
    time_arr = np.array(ordered_df[start:end + 1]['Time'])
    tdelta = datetime.strptime(str(time_arr[-1]), FMT) - datetime.strptime(str(time_arr[0]), FMT)

    if day_index not in duration_dict.keys():  
        duration_dict[day_index] = [tdelta.seconds]

    else:  
        duration_dict[day_index].append(tdelta.seconds)

    # trip latitudes and longitudes
    init_latitude = latitudes[current_trip][0]
    dest_latitude = latitudes[current_trip][-1]

    init_longitude = longitudes[current_trip][0]
    dest_longitude = longitudes[current_trip][-1]

    dist = calculateDistance(init_latitude, init_longitude, dest_latitude, dest_longitude)

    if day_index not in distance_dict.keys():  
        distance_dict[day_index] = [dist]

    else:  
        distance_dict[day_index].append(dist)

    current_trip += 1

a, b, c = calculateDistanceStats(distance_dict, total_items=len(trips))
print('Total distance is ', a)
print('Average distance is ', b)
print('Daily average distances are ', c)
print(calculateTimeStats(duration_dict))

# STOP POINTS
prev = None
current_trip = 0
long_stops = []
short_stops = []
for start, end in trips:
    if prev is not None:

        trip_start_time = np.array(ordered_df[start:start + 1]['Time'])[0]
        trip_start_lat = np.array(ordered_df[start:start + 1]['Latitude'])[0]
        trip_start_lon = np.array(ordered_df[start:start + 1]['Longitude'])[0]

        tdelta = datetime.strptime(str(trip_start_time), FMT) - datetime.strptime(str(prev), FMT)

        # print(current_trip, round(tdelta.seconds/60, 4), trip_start_lat)

        if tdelta.seconds >= 4 * 3600:  # 4 hours
            long_stops.append((trip_start_lat, trip_start_lon))
            
        elif tdelta.seconds >= 30 * 60:  # 30 mins
            short_stops.append((trip_start_lat, trip_start_lon))

    prev = np.array(ordered_df[end:end + 1]['Time'])[0]
    current_trip += 1

displayStopPoints(bboxes[-1], long_stops, short_stops, map='map.png', path=FIGURES_DIR)





print("HTTP calls for postcode frequency !!!")
short_zips = getZipCodeFrequency(short_stops[:], api)
long_zips = getZipCodeFrequency(long_stops[:], api)
print("Short stop zips: ", short_zips, 'duration: ', tdelta.seconds)
print("Long stop zips: ", long_zips)

# Read Charge Point Dataset
df = pandas.read_csv('uk_registry.csv', lineterminator='\n')
df['longitude'] = df['longitude'].astype(float)
df['latitude'] = df['latitude'].astype(float)

# put postcode prefixes in a dictionary
postcode_device_dict = {} # key: postcode, value: list of charging points

for index, row in df.iterrows():
    try:
        postcode = row['postcode'].split()[0] 
        deviceId = row['chargeDeviceID']
        if postcode not in postcode_device_dict.keys():
            postcode_device_dict[postcode] = [deviceId]
        else:
            postcode_device_dict[postcode].append(deviceId)
    except:
        if row['postcode'] == 'nan':  # eliminate null postcodes
            print(index, row['postcode'])

print("Number of postcode prefix is " + str(len(postcode_device_dict.keys())))

short_stop_postcodes = list(short_zips.keys())
long_stop_postcodes = list(long_zips.keys())
#print(short_stop_postcodes, long_stop_postcodes)


# Charging stations at short stop points 
postcode_numcharging_point_dict = {}
for postcode in short_stop_postcodes:
    if postcode in postcode_device_dict:
        charging_points = postcode_device_dict[postcode]
        postcode_numcharging_point_dict[postcode] = len(charging_points)
    else:
        print(postcode + " is not in the charging points list")

# Charging stations at long stop points  
for postcode in long_stop_postcodes:
    if postcode in postcode_device_dict:
        charging_points = postcode_device_dict[postcode]
        postcode_numcharging_point_dict[postcode] = len(charging_points)
    else:
        print(postcode + " is not in the charging points list")

print(postcode_numcharging_point_dict)



#CALCULATING AVG SPEED

speedlist = []
tdeltas = []
xdeltas = []
for start,end in trips:
    current = ordered_df[start:end+1]
    
    times = np.array(current['Time'])

    tdelta = datetime.strptime(str(times[-1]), FMT) - datetime.strptime(str(times[0]), FMT)
    tdelta_hour = tdelta.seconds/3600
    
    latitudes = np.array(current['Latitude'])
    longitudes = np.array(current['Longitude'])


    xdelta = calculateDistance(latitudes[0], longitudes[0], latitudes[-1], longitudes[-1])
    
    speed = xdelta / tdelta_hour
    speed = round(speed, 3)
    speedlist.append(speed)
    
    tdeltas.append(tdelta_hour)
    xdeltas.append(xdelta)
    
    #print(xdelta, tdelta_hour)
    #print(speed)
    #break

#speedlist    

#print('Average speed of trips of driver 1 is  ', calculateSpeed(ordered_df,trips))



data = {'home_latitude':[], 'home_longitude':[], 'dest_latitude' : [], 'dest_longitude' : []} 
for start,end in trips:
    current = ordered_df[start:end+1]
    
    latitudes = np.array(current['Latitude'])
    longitudes = np.array(current['Longitude'])
    
    data['home_latitude'].append(latitudes[0])
    data['dest_latitude'].append(latitudes[-1])
    
    data['home_longitude'].append(longitudes[0])
    data['dest_longitude'].append(longitudes[-1])
    
routes_df = pandas.DataFrame(data)
routes_df.head()

speed_df = pandas.read_csv("speeds.csv")


speed_df = speed_df.sort_values(by=['speed'], ascending=True, inplace=False)

slist = list(speed_df['speed'])
print(slist)

