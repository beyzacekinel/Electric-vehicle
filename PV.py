#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  7 22:37:47 2021

@author: beyza
"""
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from pvlib import location
from pvlib import irradiance
from datetime import datetime, timedelta


DRIVER = "Driver18"


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
# set starting index as zero
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

        elif prevDayIndex != row['Day Index']: # new day started
            if prevIndex - tripStartIndex > 3: # minimum 4 significant points
                trips.append((tripStartIndex, prevIndex)) 

            prevDayIndex = row['Day Index']
            tripStartIndex = index

        else: # aynı günse
            # önceki veriyle zaman farkını hesapla
            tdelta = datetime.strptime(str(row['Time']), FMT) - datetime.strptime(str(prevTime), FMT)
            #print(tdelta, tdelta.seconds)

            if tdelta.seconds >= 5*60: 
                # time difference >= 5 minutes 
                if prevIndex - tripStartIndex > 3: # minimum 4 significant points
                    trips.append((tripStartIndex, prevIndex)) 
                tripStartIndex = index

            else: # skip if stayed in the same coordinate
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

winter_irradiance = get_irradiance(site, '12-21-2019',10,180)

#convert df indexes to Hour:Minute format to make plotting easier
summer_irradiance.index = summer_irradiance.index.strftime("%H:%M")
winter_irradiance.index = winter_irradiance.index.strftime("%H:%M")


driver_stats = pd.read_excel('birdflight vs mapbox/birdflight_vs_mapbox.xlsx', sheet_name=DRIVER)

mapbox_distances = np.array(driver_stats['mapbox_distance'])

prev = None
energy = 24 # 80% EFFICIENCY (30*0.8)
energies = [energy]

cum_dists = [0]
cum_times = [0]

current_trip = 0
required_hour = 0 # how many more hours are required for the first charge after energy < 0 

fail = 0 # keep track of trips in which energy < 0 

SOC = []
chargecount = 0

for start, end in trips:
    solar_gain = 0
    
    trip_lats = np.array(ordered_df[start:end+1]['Latitude'])
    trip_longs = np.array(ordered_df[start:end+1]['Longitude'])
    trip_times = np.array(ordered_df[start:end+1]['Time'])
    
    for i in range(len(trip_times)):
        time = trip_times[i].strftime("%H:%M")
        
        
        solar_gain += winter_irradiance['GHI'][time] / 60000     #converting to kwh  # Summer or Winter change accordingly
       
        
        #print("SOLAR GAIN= ", solar_gain)
        #print( solar_gain * 1/60)

            
        
    duration = datetime.strptime(str(trip_times[-1]), FMT) - datetime.strptime(str(trip_times[0]), FMT)
    #print(round(solar_gain, 2), round(solar_gain / (duration.seconds/60), 3))
    #print(trip_times[0], trip_times[-1])
    
    #dist = calculateDistance(trip_lats[0], trip_longs[0], trip_lats[-1], trip_longs[-1]) # KUŞ BAKIŞI
    dist = mapbox_distances[current_trip] # MAPBOX DISTANCES
    cum_dists.append(cum_dists[-1] + dist)
    
    loss = 0.174*dist # YOL BOYU HARCANAN
    #print("loss: ", loss)
    energy = energy + solar_gain - loss
    #print("ENERGY= ", energy, "SOLAR GAIN= ", solar_gain)
    
    if energy >= 24:
        energy = 24
        chargecount +=1
    energies.append(energy)
        
   
    
    if energy < 0:
        #print("current trip is: ", current_trip + 1)
        fail +=1
        
        
        
    percent_charge = (energy / 24) 
    #print("PERCENT OF CHARGE IS " ,percent_charge)
    
    SOC.append(percent_charge)    
        
        
        
    
    
    trip_time = datetime.strptime(str(trip_times[-1]), FMT) - datetime.strptime(str(trip_times[0]), FMT)
    cum_times.append(cum_times[-1] + trip_time.seconds/3600)
    
    prev = trip_times[-1]
    current_trip += 1
    


#print("FINAL ENERGY = " , energies[-1]) 
#print("TOTAL FAILURES = ", fail) 

print("FINAL STATE OF CHARGE IS : % ", energies[-1] * 100 / 24)

#print("AVG STATE OF CHARGE IS % ", sum(SOC)/len(SOC)* 100)

print("Batteries are fulled ", chargecount, "times ")





  
 
plt.plot(cum_dists, energies, color="blue")
plt.xlabel("Trip Distance (km)")
plt.ylabel(" PV Energy Consumption (kWh)")
plt.title("Distance vs Energy Consumption for "+DRIVER )
#plt.savefig("energy_plots/"+DRIVER+"_Distance.png")

plt.close()




plt.plot(cum_times, energies, color="green")

plt.xlabel("Trip Time (h)")
plt.ylabel("Energy (kWh)")
plt.title("Time vs Energy Consumption for "+ DRIVER)
#plt.savefig("energy_plots/"+DRIVER+"_Time.png")
plt.close()


