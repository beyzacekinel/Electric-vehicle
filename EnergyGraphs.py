#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 30 15:19:54 2021

@author: beyza
"""
import pandas
import numpy as np
from math import sin, cos, sqrt, atan2, radians, sqrt
import geopy.distance


import matplotlib.pyplot as plt

from datetime import datetime, timedelta

from utils import *

DRIVER = "Driver07"
HOME_ZIP = "NW4"


required_hour = 0 #how many more hours are required for the first charge after energy<0


# ******** ALL LONG/SHORT STOP CHARGING PLOTS **********


df = pandas.read_csv('wo_date_weekday/' + DRIVER + '.csv')

clean_df = df.drop(0)

clean_df['Longitude'] = clean_df['Longitude'].astype(float)
clean_df['Latitude'] = clean_df['Latitude'].astype(float)

clean_df['Day Index'] = clean_df['Day Index'].astype(int)

clean_df['Time'] = pandas.to_datetime(clean_df['Time'], format='%H:%M:%S').dt.time
ordered_df = clean_df.sort_values(by=['Day Index', 'Time'], ascending=True, inplace=False)

ordered_df.reset_index(drop=True, inplace=True)

prevDayIndex = None
prevTime = None
prevIndex = None
prevRow = None

tripStartIndex = None
trips = []

for index, row in ordered_df.iterrows():
    
    if prevTime is None: # read the first
        prevDayIndex = row['Day Index']
        tripStartIndex = index
    
    elif prevDayIndex != row['Day Index']: # new day has started
        if prevIndex - tripStartIndex > 3: # minimum 4 significant points
            trips.append((tripStartIndex, prevIndex)) # add this trip
        
        prevDayIndex = row['Day Index']
        tripStartIndex = index
        
    else: # if same day
        # calculate the time difference
        FMT = '%H:%M:%S'
        tdelta = datetime.strptime(str(row['Time']), FMT) - datetime.strptime(str(prevTime), FMT)
        #print(tdelta, tdelta.seconds)
        
        if tdelta.seconds >= 5*60: 
            # if time difference >= 5 minutes
            if prevIndex - tripStartIndex > 3: # 3 significant data points
                trips.append((tripStartIndex, prevIndex)) # add this trip
            tripStartIndex = index
            
        else: # stayed in the same coordinate
            if prevRow['Latitude'] == row['Latitude'] and prevRow['Longitude'] == row['Longitude']:
                prevRow = row
                continue
            
    prevTime = row['Time']
    prevIndex = index
    prevRow = row
    


FMT = '%H:%M:%S'
current_trip = 0 # highlights the index that i'm tracing in the trip array


prev = None

long_stops = []
short_stops = []
for start, end in trips:
    if prev is not None:
        
        trip_start_time = np.array(ordered_df[start:start+1]['Time'])[0]
        trip_start_lat = np.array(ordered_df[start:start+1]['Latitude'])[0]
        trip_start_lon = np.array(ordered_df[start:start+1]['Longitude'])[0]
        
        tdelta = datetime.strptime(str(trip_start_time), FMT) - datetime.strptime(str(prev), FMT)
        
        #print(current_trip, round(tdelta.seconds/60, 4), trip_start_lat)
        
        if tdelta.seconds >= 4*3600: # 4 hours
            long_stops.append((trip_start_lat, trip_start_lon, tdelta.seconds/3600))
        elif tdelta.seconds >= 30*60: # 30 mins
            short_stops.append((trip_start_lat, trip_start_lon, tdelta.seconds/60))
        
    prev = np.array(ordered_df[end:end+1]['Time'])[0]
    current_trip += 1


#API    
import postcodes.postcodes_io_api as postcodes_io_api

api  = postcodes_io_api.Api(debug_http=False)

data = api.get_nearest_postcodes_for_coordinates(latitude=51.466324,longitude=-0.173606,limit=1)
#result = data['result'][0]
#result['postcode'] 


#CHARGING STRATEGIES

prev = None

energy = 30
energies = [energy]

cum_dists = [0]
cum_times = [0]
current_trip = 0

fail = 0 # keep track of trips in which energy < 0 

driver_stats = pandas.read_excel('birdflight vs mapbox/birdflight_vs_mapbox.xlsx', sheet_name=DRIVER)
mapbox_distances = np.array(driver_stats['mapbox_distance'])


for start, end in trips:
    
    
    trip_lats = np.array(ordered_df[start:end+1]['Latitude'])
    trip_longs = np.array(ordered_df[start:end+1]['Longitude'])
    
    trip_times = np.array(ordered_df[start:end+1]['Time'])
    
    if prev is not None: 
        tdelta = datetime.strptime(str(trip_times[0]), FMT) - datetime.strptime(str(prev), FMT) # stop time
        
        #if tdelta.seconds >= 30*60: # ( !!! BEST CASE = SCENARIO 4 !!! ) 
        if tdelta.seconds >= 4*3600  : # if a stay is longer than 4 hours (!!! LONG STOPS !!!)
        #if tdelta.seconds >=30*60 and tdelta.seconds < 4*3600: #(!!! SHORT STOPS !!! )
            data = api.get_nearest_postcodes_for_coordinates(latitude=trip_lats[0],longitude=trip_longs[0],limit=1)
            if data['result'] is not None:
                result = data['result'][0]
                postcode = result['postcode']
                postcode = postcode.split()[0] # prefix kısmı
                
                #if postcode == HOME_ZIP :    ( !!! CHARGING AT HOME !!! )
                charge_cap = 6.6 # hourly charging capacity
                                
                new_cap = energy + (tdelta.seconds / 3600) * 6.6
                if new_cap > 30:
                    energy = 30
                else:
                    energy = new_cap
                                    
                energies.append(energy)
                cum_dists.append(cum_dists[-1])
                cum_times.append(cum_times[-1] + tdelta.seconds/3600)
                    
    
    
    #dist = calculateDistance(trip_lats[0], trip_longs[0], trip_lats[-1], trip_longs[-1]) # bird-eye view distance
    dist = mapbox_distances[current_trip] # MAPBOX DISTANCES   
    cum_dists.append(cum_dists[-1] + dist)
    
    energy = energy - 0.174*dist 
    energies.append(energy)
    
    
    if energy < 0:
        required_hour += -energy / 6.6
        fail += 1
    
    trip_time = datetime.strptime(str(trip_times[-1]), FMT) - datetime.strptime(str(trip_times[0]), FMT)
    cum_times.append(cum_times[-1] + trip_time.seconds/3600)
    
    prev = trip_times[-1]
    current_trip += 1

#print(cum_times)

#print("Required time for needed charge is ", required_hour, "hours")


print("NUMBER OF FAILED TRIPS =  ", fail)



#PLOT ENERGY-DISTANCE
plt.plot(cum_dists, energies, color="blue")

plt.xlabel("Trip Distance (km)")
plt.ylabel("Energy (kWh)")
plt.title("Mapbox Distance vs Energy Consumption for " + DRIVER)
#plt.savefig("energy_plots/" + DRIVER + "_Distance.png")
#plt.close()


#PLOT ENERGY-TIME
plt.plot(cum_times, energies, color="green")

plt.xlabel("Trip Time (h)")
plt.ylabel("Energy (kWh)")
plt.title("Mapbox Time vs Energy Consumption for " + DRIVER)
plt.savefig("energy_plots/" + DRIVER + "_Time.png")
plt.close()




#PLOT STATE OF CHARGE

power = np.array(energies)
power = np.divide(power, 30/100)
plt.plot(cum_times, power, color="yellow")

plt.xlabel("Trip Time (h)")
plt.ylabel(" % Power (kW)")
plt.title("Time vs Power for Driver03")
plt.savefig("energy_plots/" +DRIVER+ "_Time.png")


