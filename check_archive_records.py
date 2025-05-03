#!/usr/bin/env python3
"""
Script to check for existing archive records in InfluxDB.
"""

import sys
import os
import time
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import weedb
import weedb.influx

def check_archives():
    """Check for archive records in InfluxDB"""
    
    print("Checking for archive records in InfluxDB...")
    
    # Connection parameters from the test config
    connection_params = {
        'host': 'localhost',
        'port': 8086,
        'org': 'weewx',
        'token': 'aXwGB3kJzQgfRD9f1ibYcsmGbmj-9DExYoK_rbbqf2yS5DgbRTNR-kHC8SPOzr9Blfs5rrAMIOsvFMvOl0dA_A==',
        'bucket': 'weather_data'
    }
    
    try:
        # Connect to InfluxDB
        print("Connecting to InfluxDB...")
        conn = weedb.influx.connect(**connection_params)
        print("Connected successfully!")
        
        # List all measurements
        print("\nListing measurements/tables:")
        tables = conn.tables()
        if tables:
            print(f"Found {len(tables)} measurements: {', '.join(tables)}")
        else:
            print("No measurements found")
            
        # Check if 'archive' measurement exists
        if 'archive' in tables:
            print("\nFound 'archive' measurement - checking for records...")
            
            # Query recent records
            cursor = conn.cursor()
            query = f'''
            from(bucket: "{conn.bucket}")
              |> range(start: -1d)
              |> filter(fn: (r) => r._measurement == "archive")
              |> limit(n: 100)
            '''
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            if results:
                print(f"Found {len(results)} archive records in the last day")
                
                # Display details of the first few records
                print("\nSample records:")
                for i, record in enumerate(results[:5]):
                    print(f"Record {i+1}: {record}")
            else:
                print("No archive records found in the last day")
        else:
            print("\nNo 'archive' measurement found - WeeWX has not written any archive records yet")
            
        # Close the connection
        conn.close()
        print("\nConnection closed.")
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_archives()