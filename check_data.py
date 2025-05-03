#!/usr/bin/env python3
"""
Script to check data in the InfluxDB bucket
"""

from influxdb_client import InfluxDBClient
from datetime import datetime

# Connection parameters
conn_params = {
    'url': 'http://localhost:8086',
    'token': '4hpJnz8A4fiH3oToXOWehFkAcdtIH-3sA7doosxvTf7iqViV0u6Q0uwinqqSA02JqFMSfzRpPF9F0tY14o8trQ==',
    'org': 'weewx',
    'bucket': 'weewx_testing'
}

print("Checking data in InfluxDB...")
client = InfluxDBClient(**conn_params)
query_api = client.query_api()

# Query recent data
query = f'''
from(bucket: "{conn_params['bucket']}")
  |> range(start: -3h)
  |> filter(fn: (r) => r._measurement == "archive")
  |> limit(n: 10)
'''

print("Executing query...")
results = query_api.query(query=query)

if results:
    print(f"Found {len(results)} tables with data")
    count = 0
    
    for table in results:
        for record in table.records:
            count += 1
            timestamp = record.get_time()
            field = record.get_field()
            value = record.get_value()
            
            print(f"Record {count}: Time={timestamp}, Field={field}, Value={value}")
    
    print(f"\nTotal records: {count}")
else:
    print("No data found")

client.close()
print("Connection closed.")