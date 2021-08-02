import geopy.distance
import postcodes.postcodes_io_api as postcodes_io_api
from datetime import datetime, timedelta


api  = postcodes_io_api.Api(debug_http=False)

def calculateDistance(lat1, lon1, lat2, lon2):

    coord1 = (lat1, lon1)
    coord2 = (lat2, lon2)

    return round(geopy.distance.distance(coord1, coord2).km, 3)


def calculateDistanceStats(distance_dict, total_items):
    sum_distance = 0
    for value in distance_dict.values():
        sum_distance += sum(value)

    # print(sum_distance)

    avg_distance = sum_distance / total_items
    #print(avg_distance) #günlük değil total

    daily_avg_dist = {}
    for k, v in distance_dict.items():
        daily_total_distance = sum(v)
        avg = (daily_total_distance / len(v))
        daily_avg_dist[k] = round(avg, 3)

    return (sum_distance, avg_distance, daily_avg_dist)


def calculateTimeStats(duration_dict):
    daily_total_time = 0
    daily_duration_dict = {}
    for k, v in duration_dict.items():
        daily_total_time = sum(v) / 60
        avg = (daily_total_time / len(v)) 
        daily_duration_dict[k] = round(avg, 3)  # in seconds
    

    return daily_duration_dict


def getZipCodeFrequency(coordinates, api, zip_limit=1):
    postcode_dict = {}
    for lat, lon in coordinates:
        data = api.get_nearest_postcodes_for_coordinates(latitude=lat, longitude=lon, limit=zip_limit)
        if data['result'] is None:
            continue
        result = data['result'][0]  # dictionary dönüyor
        postcode = result['postcode'].split()[0]  # postcode çektim

        if postcode not in postcode_dict.keys():
            postcode_dict[postcode] = 1

        else:
            postcode_dict[postcode] = postcode_dict[postcode] + 1

    return postcode_dict


"""

def calculateSpeed(orderedf, trips):
    for start,end in trips:
        current = ordered_df[start:end+1]
        
        times = np.array(current['Time'])
    
        tdelta = datetime.strptime(str(times[-1]), FMT) - datetime.strptime(str(times[0]), FMT)
        tdelta = tdelta.seconds/3600
        
        latitudes = np.array(current['Latitude'])
        longitudes = np.array(current['Longitude'])
    
    
        xdelta = calculateDistance(latitudes[0], longitudes[0], latitudes[-1], longitudes[-1])
        avg_speed = xdelta / tdelta
    return (round(avg_speed, 3))




"""






