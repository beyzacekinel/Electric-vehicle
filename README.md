# A Feasibility Study of Electric Vehicles in UK

“utils” class includes calculateDistance, calculateDistanceStats, calculateTimeStats, 
getZipCodeFrequency functions. 

calculateDistance: calculates the distance between two geographical coordinates consisting of latitudes and longitudes

calculateDistanceStats: returns the total distance, average distance and daily average distance

calculateTimeStats: returns a dictionary of daily trip durations

getZipCodeFrequency: outputs postcode dictionary in which keys are postcodes in London and values are the frequency of stays in that postcode


“EnergyGraphs” calls “utils” module and visualize energy graphs as well as state of charge. 

“Exp” module utilizes the curve fit for speed data

“PV” module simulates PV model but consider charging only during trip times

“PV_alltime” module simulates PV model by considering all time charging which includes travelling and staying durations.

“Mapping” includes displayRoute, displayAllRoutes, displayStopPoints, create_route_geojson, create_walking_route modules.

displayRoute: plots and saves each trip route visually

displayAllRoutes: plots all trips of a driver in a single map 

displayStopPoints: plots all stopping points, including short and long stops, in a single map

create_route_geojson and create_walking_route are used for Mapbox API integration in order to reach Mapbox data using Python.

“MonthlyCharging” module simulates the model in a monthly basis such that every month’s solar irradiation effect can be observed.
