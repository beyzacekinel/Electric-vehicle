#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug  1 13:05:00 2021

@author: beyza
"""
import numpy as np
from datetime import datetime, timedelta

import pandas as pd
from matplotlib import pyplot as plt
from pvlib import location
from pvlib import irradiance


DRIVER = "Driver18"

#period = "winter"



#READ DATASET, FIND TRIPS

df = pd.read_csv('wo_date_weekday/raw_'+DRIVER +'.csv')
# Clean the dataframe
clean_df = df.drop(0)
clean_df['Longitude'] = clean_df['Longitude'].astype(float)
clean_df['Latitude'] = clean_df['Latitude'].astype(float)
clean_df['Day Index'] = clean_df['Day Index'].astype(int)
clean_df['Time'] = pd.to_datetime(clean_df['Time'], format='%H:%M:%S').dt.time
# Order the dataframe by "Day Index" and "Time" in ascending order
ordered_df = clean_df.sort_values(by=['Day Index', 'Time'], ascending=True, inplace=False)
# indexi sıfırdan başlat
ordered_df.reset_index(drop=True, inplace=True)



FMT = '%H:%M:%S'
def extractTrips(ordered_df):
    prevDayIndex = None
    prevTime = None
    prevIndex = None
    prevRow = None

    tripStartIndex = None
    trips = []

    for index, row in ordered_df.iterrows():

        if prevTime is None: # read the first data
            prevDayIndex = row['Day Index']
            tripStartIndex = index

        elif prevDayIndex != row['Day Index']: # new day has started
            if prevIndex - tripStartIndex > 3: # minimum 4 significant points
                trips.append((tripStartIndex, prevIndex)) # add this trip

            prevDayIndex = row['Day Index']
            tripStartIndex = index

        else: # same day
            # calculate time difference with the previous
            tdelta = datetime.strptime(str(row['Time']), FMT) - datetime.strptime(str(prevTime), FMT)
            #print(tdelta, tdelta.seconds)

            if tdelta.seconds >= 5*60: 
                # if time difference >= 5 minutes
                if prevIndex - tripStartIndex > 3: # minimum 4 significant points
                    trips.append((tripStartIndex, prevIndex)) # add this trip
                tripStartIndex = index

            else: # stayed in the same coordinate
                if prevRow['Latitude'] == row['Latitude'] and prevRow['Longitude'] == row['Longitude']:
                    prevRow = row
                    continue

        prevTime = row['Time']
        prevIndex = index
        prevRow = row
        
    return trips

trips = extractTrips(ordered_df) 






#PV CALCULATION !!!!!!!!!!!!!

tz = 'Etc/Greenwich'
lat,lon = 51, -0.1

#Create location object to store lat, lon, timezone
site = location.Location(lat,lon,tz = tz)

#Calculate clear-sky GHI and transpose to plane of array
#Define a function so that we can reuse the sequence of operations with different locations

def get_irradiance(site_location, date, tilt, surface_azimuth):
    #creates one day's worth of 10 min intervals
    times = pd.date_range(date, freq = '1 min', periods = 60*24, tz = site_location.tz)
    
    #Generate clearsky data using the Ineichen model, which is the default
    #The get_clearsky method returns a df with values for GHI, DNI, DHI
    clearsky = site_location.get_clearsky(times)
    
    #Get solar azimuth and zenith to pass to the transposition function
    solar_position = site_location.get_solarposition(times = times)
    
    #Use the get_total_irradiance function to transpose the GHI to POA
    POA_irradiance = irradiance.get_total_irradiance(
        surface_tilt = tilt,
        surface_azimuth = surface_azimuth,
        dni = clearsky['dni'],
        ghi = clearsky['ghi'],
        dhi = clearsky['dhi'],
        solar_zenith = solar_position['apparent_zenith'],
        solar_azimuth = solar_position['azimuth'])
    
    #Return df with only GHI nd POA
    return pd.DataFrame({'GHI': clearsky['ghi'], 'POA': POA_irradiance['poa_global']})



#Get irradiance data for summer and winter solstice, assuming 10 degree tilt and a south facing array

summer_irradiance = get_irradiance(site, '06-21-2019',10,180)

winter_irradiance = get_irradiance(site, '21-12-2019',10,180)

#convert df indexes to Hour:Minute format to make plotting easier
summer_irradiance.index = summer_irradiance.index.strftime("%H:%M")
winter_irradiance.index = winter_irradiance.index.strftime("%H:%M")


irradiance_dict = {"winter": winter_irradiance['GHI'], "summer" : summer_irradiance['GHI']}


driver_stats = pd.read_excel('birdflight vs mapbox/birdflight_vs_mapbox.xlsx', sheet_name=DRIVER)



mapbox_distances = np.array(driver_stats['mapbox_distance'])

def addMins(tm, mins):
    fulldate = datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
    fulldate = fulldate + timedelta(minutes=mins)
    return fulldate.time()


prev = None
energy = 24
energies = [energy]

cum_dists = [0]
cum_times = [0]

current_trip = 0

solar_gain_car = 0
solar_gain_day = 0

day_index = None

daily_solar = {}

current_day = datetime(2019,6,1) #Y-M-D
day_counter = 1
day_irradiance = get_irradiance(site, current_day.strftime("%m-%d-%Y"),10,180) 
day_irradiance.index = day_irradiance.index.strftime("%H:%M")


SOC = []
fail = 0 #keep track of trips where energy < 0

chargecount = 0 #records how many times charge is refulled




for start, end in trips:
    solar_gain = 0
    
    trip_lats = np.array(ordered_df[start:end+1]['Latitude'])
    trip_longs = np.array(ordered_df[start:end+1]['Longitude'])
    trip_times = np.array(ordered_df[start:end+1]['Time'])
    day = np.array(ordered_df[start:end+1]['Day Index'])[0]
    
    if day != day_index:
        if day_index != None and day_index not in daily_solar.keys():
            daily_solar[day_index] = solar_gain_day
            
            
            
            current_day += timedelta(days=1)
            day_irradiance = get_irradiance(site, current_day.strftime("%m-%d-%Y"),10,180) 
            day_irradiance.index = day_irradiance.index.strftime("%H:%M")
            #print(current_day.strftime("%m-%d-%Y"), day_irradiance['GHI']['09:00'])
            day_counter += 1
                
            
        elif day_index != None:
            daily_solar[day_index] += solar_gain_day
        
        solar_gain_day = 0
        day_index = day
    
    for i in range(len(trip_times)):
        # ******** pvlib solar calculations ********
        time = trip_times[i].strftime("%H:%M")
        #solar_gain = solar_gain + irradiance_dict[day_irradiance][time] / 60000     # ---------- W or S ---------
        solar_gain = solar_gain +  day_irradiance['GHI'][time] / 60000
        
        
    #duration = datetime.strptime(str(trip_times[-1]), FMT) - datetime.strptime(str(trip_times[0]), FMT)
    #print(round(solar_gain, 2), round(solar_gain / (duration.seconds/60), 3))
    #print(trip_times[0], trip_times[-1])
    
    solar_gain_stop = 0
    if prev is not None: # during a stopping position
        solar_gain_stop = 0
        tdelta = datetime.strptime(str(trip_times[0]), FMT) - datetime.strptime(str(prev), FMT) # stop time
        
    
        mins = tdelta.seconds // 60
        
        time_change = timedelta(hours=mins)
        
        #print(prev, mins)
        
        for i in range(mins): #solar gain during a stay
            t = addMins(prev, i).strftime("%H:%M")
            solar_gain_stop +=  day_irradiance['GHI'][t] / 60000
            
            if t == "00:00":
                if day_index != None and day_index-1 not in daily_solar.keys():
                    daily_solar[day_index-1] = solar_gain_stop
                elif day_index != None:
                    daily_solar[day_index-1] += solar_gain_stop
                    
                solar_gain_day -= solar_gain_stop
            
        energy += solar_gain_stop
        
        if energy >= 24:
            energy = 24
            chargecount +=1
            
        energies.append(energy)
        cum_dists.append(cum_dists[-1])
        cum_times.append(cum_times[-1] + tdelta.seconds/3600)
        

    
    init_energy = energies[-1]
    
    #dist = calculateDistance(trip_lats[0], trip_longs[0], trip_lats[-1], trip_longs[-1]) # KUŞ BAKIŞI
    dist = mapbox_distances[current_trip] # MAPBOX DISTANCES
    cum_dists.append(cum_dists[-1] + dist)
    
    loss = 0.174*dist # energy consumption during a travel 
    energy = energy + solar_gain - loss
    
    if energy >= 24:
        energy = 24
        chargecount +=1
        
    energies.append(energy)
    
    if energy < 0:
        fail += 1 
        #print("current trip is: ", current_trip + 1)
        
    
    
    percent_charge = (energy / 24) * 100
    #print("PERCENT OF CHARGE IS " ,percent_charge)
    
    SOC.append(percent_charge)
    
    
    
    
    
    #print(init_energy, energy)

    
    
    
    trip_time = datetime.strptime(str(trip_times[-1]), FMT) - datetime.strptime(str(trip_times[0]), FMT)
    cum_times.append(cum_times[-1] + trip_time.seconds/3600)
    
    prev = trip_times[-1]
    current_trip += 1
 


    
print("TOTAL FAILURES IN TRIPS = ", fail) 
    

power = np.array(energies)
power = np.divide(power, 24/100)

#print("FINAL STATE OF CHARGE IS : % ", power[-1])


#print("Batteries are fulled ", chargecount, "times ")

#print("UNUSED ENERGY IS ", unused_energy)