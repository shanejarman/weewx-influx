#!/usr/bin/env python3
"""
Simple script to test the InfluxDB driver for WeeWX.
Streams weather data for approximately 10 seconds, generating at least 5 data points.
"""

import sys
import os
import time
import random
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import weedb
import weedb.influx

def test_connection():
    """Test connecting to InfluxDB and stream data for 10 seconds"""
    
    print("Testing InfluxDB connection...")
    
    # Connection parameters
    connection_params = {
        'host': 'localhost',
        'port': 8086,
        'org': 'weewx',
        'token': 'aXwGB3kJzQgfRD9f1ibYcsmGbmj-9DExYoK_rbbqf2yS5DgbRTNR-kHC8SPOzr9Blfs5rrAMIOsvFMvOl0dA_A==',
        'bucket': 'weather_data'
    }
    
    try:
        # Try to connect
        print("Connecting to InfluxDB...")
        conn = weedb.influx.connect(**connection_params)
        print("Connected successfully!")
        
        # Try to list measurements (tables)
        print("\nListing measurements/tables:")
        tables = conn.tables()
        if tables:
            print(f"Found {len(tables)} measurements: {', '.join(tables)}")
        
        # Stream data for approximately 10 seconds
        print("\nStreaming weather data for 10 seconds...")
        from influxdb_client import Point
        
        # Initial values - realistic weather values
        temperature = 72.5  # Fahrenheit
        humidity = 60.3     # Percent
        pressure = 1013.2   # hPa
        wind_speed = 5.2    # mph
        wind_dir = 180      # degrees
        rain = 0.0          # inches
        
        # Set start time and count
        start_time = time.time()
        end_time = start_time + 10  # Stream for 10 seconds
        count = 0
        
        # Stream data points until 10 seconds have passed
        while time.time() < end_time:
            # Create a timestamp
            current_time = datetime.utcnow()
            
            # Add small random variations to create realistic data
            temperature += random.uniform(-0.3, 0.3)
            humidity += random.uniform(-1.0, 1.0)
            pressure += random.uniform(-0.1, 0.1)
            wind_speed += random.uniform(-0.5, 0.5)
            wind_dir = (wind_dir + random.uniform(-5, 5)) % 360
            rain += random.uniform(0, 0.01) if random.random() > 0.8 else 0
            
            # Keep values in realistic ranges
            humidity = max(0, min(100, humidity))
            wind_speed = max(0, wind_speed)
            
            # Create a point
            point = Point("weather_data")\
                .tag("source", "weewx_test")\
                .field("temperature", round(temperature, 1))\
                .field("humidity", round(humidity, 1))\
                .field("pressure", round(pressure, 1))\
                .field("wind_speed", round(wind_speed, 1))\
                .field("wind_dir", round(wind_dir, 0))\
                .field("rain", round(rain, 2))\
                .time(current_time)
                
            # Write the point
            conn.write_api.write(bucket=conn.bucket, org=conn.org, record=point)
            count += 1
            
            print(f"Data point {count} written: temp={round(temperature, 1)}°F, humidity={round(humidity, 1)}%, pressure={round(pressure, 1)}hPa")
            
            # Sleep for ~2 seconds to get about 5 data points over 10 seconds
            time.sleep(2)
            
        print(f"\nStreaming complete! Wrote {count} data points over {round(time.time() - start_time, 1)} seconds.")
            
        # Try a simple query to get the data back
        print("\nRetrieving test data:")
        cursor = conn.cursor()
        query = f'''
        from(bucket: "{conn.bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "weather_data")
          |> limit(n: 10)
        '''
        
        cursor.execute(query)
        results = cursor.fetchall()
        print(f"Retrieved {len(results)} recent records")
        
        # Close the connection
        conn.close()
        print("\nConnection closed.")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    result = test_connection()
    sys.exit(0 if result else 1)