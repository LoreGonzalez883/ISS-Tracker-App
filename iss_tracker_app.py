#!/usr/bin/env python3

import requests
import xmltodict
import logging
import argparse
import socket
from typing import List
import time
import math
from flask import Flask, request
from geopy.geocoders import Nominatim

MEAN_EARTH_RADIUS = 6378.1
J2K_TIMESTAMP = '2000-045T12:00:00.000Z'


def get_data():
    response = requests.get('https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
    data = xmltodict.parse(response.content)
    return data['ndm']['oem']['body']['segment']['data']['stateVector']

def calc_speed_3d(x: float, y: float, z: float):
    """
        This function calculates the magnitude of the speed of a particle given the velocity values in the x, y, and z directions.

    Args:
        x (float): The velocity in the x direction
        y (float): The velocity in the y direction
        z (float): The velocity in the z direction

    Returns:
        speed (float): The calculated magnitude of the speed
    """
    try:
        speed = math.sqrt(x**2 + y**2 + z**2)
    except TypeError:
        logging.error("Non numerical values detected. Calculation cannot be performed")
        speed = 0.0
    return speed

def current_location(list_of_dicts: List[dict], key_string: str):
    """
        This function takes the current time in UTC and return the data corresponding 
        to the most recent epoch timestamp in the data.

    Args:
        list_of_dicts (List[dict]): A list of dictionaries containing each item's epoch values.
        key_string (str): The key string that corresponds to the epoch value of the item.

    Returns:
        dict: The dictionary containing the data for the most recent epoch timestamp.
    """
    current_time = time.time()
    logging.debug("current time: " + str(current_time))

    curr_index = 0
    try:
        for item in list_of_dicts:
            epoch = item[key_string][:17] 
            epoch_time_obj = time.strptime(epoch, '%Y-%jT%H:%M:%S')
            epoch_time = time.mktime(epoch_time_obj)
            
            if(current_time < epoch_time):
                #print(epoch_time_list)
                logging.debug("epoch time: " + str(epoch_time))
                break
            curr_index += 1
    except ValueError:
        #throw an error that the epoch timestring is not in the correct format
        logging.error("Invalid time format, ensure that the epoch timestring is in the format 'yyyy-dddThh:mm:ss.xxxZ'. Empty python dictionary returned.")
        return {}
        
    return list_of_dicts[curr_index-1]

def find_location(x: float, y: float, z: float, epoch:str):
    """
        This function calculates approximate location data based on xyz coordinates and the time of the location.

        Args:
            x (float): The x coordinate of the ISS
            y (float): The y coordinate of the ISS
            z (float): The z coordinate of the ISS
            epoch (str): The epoch time string given in the format yyyy-dddThh:mm:ss
    
        Returns:
            (list[str]): The list containing the calculated latitude and longitude coordinates, the altitude in km, and the approximate nearest location.

    """
    try:
        hrs = int(epoch[9:11])
        mins = int(epoch[12:14])
    except ValueError:
        logging.error("Invalid time format, ensure that the epoch timestring is in the format 'yyyy-dddThh:mm:ss.xxxZ'. Empty list returned.")
        return []

    latitude = math.degrees(math.atan2(z, math.sqrt(x**2 + y**2)))

    longitude = math.degrees(math.atan2(y, x)) - ((hrs-12)+(mins/60))*(360/24) + 19
    logging.debug('longitude before conversion' + str(longitude))

    if longitude > 180:
        longitude = -180 + (longitude - 180)
    elif longitude < -180:
        longitude = 180 + (longitude + 180)

    altitude = math.sqrt(x**2 + y**2 + z**2) - MEAN_EARTH_RADIUS

    geocoder = Nominatim(user_agent='iss_tracker_app')
    geolocation = geocoder.reverse((latitude, longitude), zoom=20, language='en')

    try:
        location = geolocation.address
    except AttributeError:
        location = "Over Ocean"

    return [str(latitude), str(longitude), str(altitude), location]


def create_app(test_config = None):
    app = Flask(__name__)

    @app.route('/comment', methods = ['GET'])
    def return_comments():
        """
            This function returns the section of the ISS data marked as comments as a list of dictionaries.

            Returns:
                comments (List[dict]): The list of dictionaries containing the comments in the data
        """

        response = requests.get('https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
        data = xmltodict.parse(response.content)

        comments = data['ndm']['oem']['body']['segment']['data']['COMMENT']
        
        for i in range (len(comments)):
            if (comments[i] == None):
                comments[i] = ''

        return comments

    @app.route('/header', methods = ['GET'])
    def return_header():
        """
            This function returns the section of the ISS data marked as the header as a dictionary.

            Returns:
                header (dict): The dictionary containing the header section in the data
        """

        response = requests.get('https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
        data = xmltodict.parse(response.content)

        header = data['ndm']['oem']['header']

        return header

    @app.route('/metadata', methods = ['GET'])
    def return_metadata():
        """
            This function returns the section of the ISS data marked as metadata as a dictionary.

            Returns:
                metadata (dict): The dictionary containing the metadata section
        """

        response = requests.get('https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
        data = xmltodict.parse(response.content)

        metadata = data['ndm']['oem']['body']['segment']['metadata']

        return metadata


    @app.route('/epochs', methods = ['GET'])
    def return_all():
        """
            This functions returns all or a section of the ISS data set based on the query parameters given.
            Returns an empty list if invalid query parameters are given.

            Returns:
                new_data (List[dict]): A list of all or a section of the ISS epoch data
        """
        data = get_data()
        limit = request.args.get('limit', len(data))
        offset = request.args.get('offset', 0)

        try:
            limit = int(limit)
        except ValueError:
            logging.error("'limit' parameter must be a positive integer")
            limit = len(data)
        try:
            offset = int(offset)
        except ValueError:
            logging.error("'offset' parameter must be a positive integer")
            offset = 0

        new_data = []
        for i in range(limit):
            if (i+offset < len(data)):
                new_data.append(data[i + offset])

        return new_data

    @app.route('/epochs/<epoch>', methods = ['GET'])
    def return_epoch(epoch: str):
        """
            This function returns a specific stateVector dictionary given a valid epoch string.

            Args:
                epoch (str): The epoch string of a specific state vector

            Returns:
                item (dict): a dictionary containing the data of the specific epoch.
        """
        data = get_data()
        for item in data:
            if item['EPOCH'] == epoch:
                return item

        logging.error("Epoch not found. Ensure that the epoch is in the format 'yyyy-dddThh:mm:ss.xxxZ'. Empty dictionary returned")
        return {}

    @app.route('/epochs/<epoch>/speed', methods = ['GET'])
    def return_epoch_speed(epoch: str):
        """
            This function returns the speed calculated based on the data of a given epoch string. If the epoch is not found, return 0.

            Args:
                epoch (str): The epoch string of a specific state vector

            Returns:
                speed (str): The magnitude of the speed of the ISS in the specified state vector. The value is returned as a string.
        """
        data = get_data()
        for item in data:
            if item['EPOCH'] == epoch:
                logging.debug(item) 
                x_dot = float(item['X_DOT']['#text'])
                y_dot = float(item['Y_DOT']['#text'])
                z_dot = float(item['Z_DOT']['#text'])
                return str(calc_speed_3d(x_dot, y_dot, z_dot)) + '\n'
        logging.error("Epoch not found. Ensure that the epoch is in the format 'yyyy-dddThh:mm:ss.xxxZ'. Zero value returned")
        return str(0.0) + '\n'

    @app.route('/epochs/<epoch>/location', methods = ['GET'])
    def return_epoch_location(epoch: str):
        """
            This function calculates the geographical location of the ISS at a given epoch using their x, y, and z position values 
            and determines the location the ISS is above geographically.
            The values calculated are the latitude, longitude, and altitude of the ISS in km. 

            Args:
                epoch (str): The epoch string of a specific state vector

            Returns:
                location_data (list[str]):
        """
        data = get_data()
        for item in data:
            if item['EPOCH'] == epoch:
                location_data = find_location(float(item['X']['#text']), float(item['Y']['#text']), float(item['Z']['#text']), item['EPOCH'])
                return location_data

        logging.error("Epoch not found. Ensure that the epoch is in the format 'yyyy-dddThh:mm:ss'. Empty list returned")
        return []

    @app.route('/now', methods = ['GET'])
    def data_now():
        """
            This function returns the state vector data and speed closest to the current time in UTC.
                
            Returns:
                statevector_now (dict): The dictionary containing the data of the epoch closest to the current time. This dictionary 
                includes the magnitude of the speed of the ISS based from the data.
        """
        data = get_data()
        statevector_now = current_location(data, 'EPOCH')
        logging.debug(statevector_now)

        x_dot = float(statevector_now['X_DOT']['#text'])
        y_dot = float(statevector_now['Y_DOT']['#text'])
        z_dot = float(statevector_now['Z_DOT']['#text'])
        speed_now = calc_speed_3d(x_dot, y_dot, z_dot)

        statevector_now['SPEED'] = speed_now

        location_now = find_location(float(statevector_now['X']['#text']), float(statevector_now['Y']['#text']), float(statevector_now['Z']['#text']), statevector_now['EPOCH'])
        statevector_now['COORDINATES'] = f'({location_now[0]}, {location_now[1]})'
        statevector_now['ALTITUDE (km)'] = location_now[2]
        statevector_now['LOCATION'] = location_now[3]

        return statevector_now
    return app
    

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--loglevel', type=str, required=False, default='WARNING',
                    help='set log level to DEBUG, INFO, WARNING, ERROR, or CRITICAL')
    args = parser.parse_args()

    format_str=f'[%(asctime)s {socket.gethostname()}] %(filename)s:%(funcName)s:%(lineno)s - %(levelname)s: %(message)s'
    logging.basicConfig(level=args.loglevel, format=format_str)
    logging.basicConfig(level=args.loglevel)

    app = create_app()
    app.run(debug=True, host='0.0.0.0')

if __name__ == '__main__':
    main()
