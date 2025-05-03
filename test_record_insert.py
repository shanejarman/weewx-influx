#!/usr/bin/env python3
"""
Script to directly test inserting WeeWX-like records into InfluxDB.
This will help us determine if the INSERT functionality is working.
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

def test_insert_records():
    """Test inserting records into InfluxDB"""
    
    print("Testing direct record insertion to InfluxDB...")
    
    # Connection parameters from the test config
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
        
        # Create a cursor for executing SQL
        cursor = conn.cursor()
        
        # Current timestamp
        timestamp = int(time.time())
        
        # Create test data (similar to what WeeWX would produce)
        for i in range(5):
            # Simulate a record with 5 minute intervals
            current_timestamp = timestamp + (i * 300)  # Add 5 minutes each time
            
            # Generate some realistic weather values
            temperature = 70.0 + random.uniform(-5, 5)
            humidity = 60.0 + random.uniform(-10, 10)
            pressure = 1013.0 + random.uniform(-5, 5)
            wind_speed = 5.0 + random.uniform(-2, 5)
            wind_dir = random.randint(0, 359)
            
            # Execute an INSERT statement similar to what WeeWX would generate
            sql = """
            INSERT INTO archive 
            (dateTime, usUnits, interval, outTemp, outHumidity, barometer, windSpeed, windDir) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(sql, (
                current_timestamp,  # dateTime
                1,                  # usUnits (US units)
                5,                  # interval (5 minutes)
                temperature,        # outTemp
                humidity,           # outHumidity
                pressure,           # barometer
                wind_speed,         # windSpeed
                wind_dir            # windDir
            ))
            
            print(f"Inserted record {i+1}: timestamp={current_timestamp}, temp={temperature:.1f}°F, humidity={humidity:.1f}%")
            
            # Small delay between inserts
            time.sleep(1)
        
        print("\nAll records inserted successfully!")
        
        # Now check if we can retrieve the records
        print("\nAttempting to retrieve the inserted records...")
        
        query = f'''
        from(bucket: "{conn.bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "archive")
          |> limit(n: 10)
        '''
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if results:
            print(f"Successfully retrieved {len(results)} records from InfluxDB")
            print("\nFirst few records:")
            for i, record in enumerate(results[:3]):
                print(f"Record {i+1}: {record}")
        else:
            print("No records found. The insertion may have failed.")
        
        # Close the connection
        conn.close()
        print("\nConnection closed.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_insert_records()