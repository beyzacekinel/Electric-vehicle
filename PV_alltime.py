#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 10 22:20:00 2021

@author: beyza
"""
import numpy as np
from datetime import datetime, timedelta

import pandas as pd
from matplotlib import pyplot as plt
from pvlib import location
from pvlib import irradiance


DRIVER = "Driver16"

period = "winter"



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

        elif prevDayIndex != row['Day Index']: # new day
            if prevIndex - tripStartIndex > 3: # minimum 4 significant points
                trips.append((tripStartIndex, prevIndex)) 

            prevDayIndex = row['Day Index']
            tripStartIndex = index

        else: # same day
            # calculate the time difference
            tdelta = datetime.strptime(str(row['Time']), FMT) - datetime.strptime(str(prevTime), FMT)
            #print(tdelta, tdelta.seconds)

            if tdelta.seconds >= 5*60: 
                #if time difference between the current and previous is => 5 minutes
                if prevIndex - tripStartIndex > 3: 
                    trips.append((tripStartIndex, prevIndex)) 
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
required_hour = 0 

SOC = []
fail = 0 #keep track of trips where energy < 0

chargecount = 0 #records how many times charge is fulled

unused_energy = 0


for start, end in trips:
    solar_gain = 0
    
    trip_lats = np.array(ordered_df[start:end+1]['Latitude'])
    trip_longs = np.array(ordered_df[start:end+1]['Longitude'])
    trip_times = np.array(ordered_df[start:end+1]['Time'])
    
    for i in range(len(trip_times)):
        # ******** pvlib solar calculations ********
        time = trip_times[i].strftime("%H:%M")
        solar_gain = solar_gain + irradiance_dict[period][time] / 60000     # ---------- W or S ---------
        
        
        
    #duration = datetime.strptime(str(trip_times[-1]), FMT) - datetime.strptime(str(trip_times[0]), FMT)
    #print(round(solar_gain, 2), round(solar_gain / (duration.seconds/60), 3))
    #print(trip_times[0], trip_times[-1])
    
    if prev is not None: 
        solar_gain_stop = 0
        tdelta = datetime.strptime(str(trip_times[0]), FMT) - datetime.strptime(str(prev), FMT) # stop time
        
    
        mins = tdelta.seconds // 60
        
        time_change = timedelta(hours=mins)
        
        #print(prev, mins)
        
        for i in range(mins):
            t = addMins(prev, i).strftime("%H:%M")
            solar_gain_stop +=  irradiance_dict[period][t] / 60000   # ---------- W or S ---------
            
            
        energy += solar_gain_stop
        
        if energy >= 24:
            unused_energy += (energy - 24)
            #print(unused_energy)
            energy = 24
            chargecount +=1
            
        energies.append(energy)
        cum_dists.append(cum_dists[-1])
        cum_times.append(cum_times[-1] + tdelta.seconds/3600)
        
            
    
    #LONG STOP CALCULATION
        if tdelta.seconds >= 4*3600: # stopped more than 4 hours 
            data = api.get_nearest_postcodes_for_coordinates(latitude=trip_lats[0],longitude=trip_longs[0],limit=1)
            if data['result'] is not None:
                result = data['result'][0]
                postcode = result['postcode']
                postcode = postcode.split()[0] # take the prefix of the postcode

                
                if postcode == "SW7": # input the home postcode
                    charge_cap = 6.6 # hourly charging capacity 
                    
                    new_cap = energy + (tdelta.seconds / 3600) * 6.6
                    if new_cap > 30:
                        energy = 30
                    else:
                        energy = new_cap

                    energies.append(energy)
                    cum_dists.append(cum_dists[-1])
                    cum_times.append(cum_times[-1] + tdelta.seconds/3600)
    
    
    init_energy = energies[-1]
    
    #dist = calculateDistance(trip_lats[0], trip_longs[0], trip_lats[-1], trip_longs[-1]) # bird-eye's view
    dist = mapbox_distances[current_trip] # MAPBOX DISTANCES
    cum_dists.append(cum_dists[-1] + dist)
    
    loss = 0.174*dist # consumption of energy during travel
    energy = energy + solar_gain - loss
    
    if energy >= 24:
        unused_energy += (energy - 24)
        #print(unused_energy)
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
 

#print("FINAL ENERGY = " , energies[-1]) #minimum energy
    
#print("TOTAL FAILURES IN TRIPS = ", fail) 
    
#print("AVG REDUCTION IN THE STATE OF CHARGE IS: % ", sum(SOC)/len(SOC))
#print("MAX REDUCTION IN THE STATE OF CHARGE IS: % ", max(SOC))

power = np.array(energies)
power = np.divide(power, 24/100)

#print("FINAL STATE OF CHARGE IS : % ", power[-1])


#print("AVG STATE OF CHARGE IS % ", sum(SOC)/len(SOC))

#print("Batteries are fulled ", chargecount, "times ")

print("UNUSED ENERGY IS ", unused_energy)

   
plt.plot(cum_dists, energies, color="blue")

plt.xlabel("Trip Distance (km)")
plt.ylabel("Energy (kWh)")
plt.title("Distance vs PV Energy Consumption for " + DRIVER)
plt.savefig("energy_plots/"+DRIVER+"_Distance.png")
plt.close()



plt.plot(cum_times, energies, color="green")

plt.xlabel("Time (h)")
plt.ylabel("Energy (kWh)")
plt.title("Time vs PV Energy Consumption for "+ DRIVER)
plt.savefig("energy_plots/"+DRIVER+"_Time.png")
plt.close()
