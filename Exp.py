# -*- coding: utf-8 -*-
"""
Created on Mon Jun 28 23:03:34 2021

@author: mehme
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

import pandas

from math import sin, cos, sqrt, atan2, radians, sqrt
import geopy.distance
#%matplotlib inline
import matplotlib.pyplot as plt
from mpl_toolkits import mplot3d

from datetime import datetime, timedelta

def func(x, a, b, c):
    return a * np.exp(-b * x) + c



#SPEED CURVE FIT

speed_df = pandas.read_csv("speeds.csv")

speed_df.sort_values(by=['speed'], ascending=True, inplace=True)

slist = np.array(speed_df['speed'])
print(slist)

intervals = np.arange(0,105,0.1)
a = slist
b = []
for i in intervals:
    x = a <= i
    b.append(sum(x)/2132)
    
x = np.array(intervals)
y = np.array(b)

plt.plot(x, y, "o", color='orange')



params = curve_fit(func, x, y)

yest = func(x, params[0][0],params[0][1],params[0][2])

print('a = ',params[0][0], 'b = ', params[0][1], 'c= ', params[0][2] )

plt.plot(x, yest, 'black', label='data')

plt.title("Cumulative Distribution of Speeds")
plt.xlabel("Speed (km/h) ")
plt.ylabel("Density")
#plt.savefig('Cumulative Distribution of Speeds.png')




"""
speed_bird = pandas.read_excel("birdflight vs mapbox/birdflight_vs_mapbox.xlsx")

speed_bird.sort_values(by=['bird_speed'], ascending=True, inplace=True)

bslist = np.array(speed_bird['bird_speed'])
print(bslist)

intervals = np.arange(0,35,0.1)
e= bslist
f = []
for i in intervals:
    x = e <= i
    f.append(sum(x)/1565)
    
x = np.array(intervals)
y = np.array(f)

plt.plot(x, y, "o", color='orange')



params = curve_fit(func, x, y)

yest = func(x, params[0][0],params[0][1],params[0][2])
plt.plot(x, yest, 'black', label='data')

plt.title("Distribution of Driver01's Speed")
plt.xlabel("Speed (km/h) ")
plt.ylabel("Density")
#plt.savefig('Cumulative Distribution of Speeds.png')


"""
