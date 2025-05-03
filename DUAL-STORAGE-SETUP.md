# Dual Storage Configuration: SQLite for Archive and InfluxDB for Real-time Data

This guide explains how to configure WeeWX to use two separate storage backends:
1. **SQLite** (or MySQL) for standard archive records (5-minute intervals)
2. **InfluxDB** for real-time LOOP data (every reading as it comes from the station)

## Introduction

WeeWX's architecture supports multiple data storage options, but the default configuration focuses on the archive data (typically at 5-minute intervals). This setup adds a custom service that captures every LOOP reading (which can be as frequent as 2-3 seconds for many stations) and sends it to InfluxDB while maintaining the standard archive functionality with SQLite.

## Prerequisites

1. Working WeeWX installation
2. InfluxDB installed and configured (see SETUP-GUIDE.md)
3. Python's influxdb-client package installed

## Configuration Steps

### 1. Install the InfluxLoop Service

First, copy the `influxloop.py` file to your WeeWX user directory:

```bash
# Create user directory if it doesn't exist
sudo mkdir -p /usr/share/weewx/user

# Copy the service file
sudo cp bin/user/influxloop.py /usr/share/weewx/user/
```

### 2. Update WeeWX Configuration

Edit your weewx.conf file to use SQLite for the regular archive and add the InfluxLoop service:

```bash
sudo nano /etc/weewx/weewx.conf
```

First, ensure your DataBindings section specifies SQLite for archive data:

```
[DataBindings]
    [[wx_binding]]
        # Use SQLite for regular archive data
        database = archive_sqlite
        # The measurement name
        table_name = archive
        # The manager handles aggregation of data for historical summaries
        manager = weewx.manager.DaySummaryManager
        # The schema defines the structure of the database
        schema = schemas.wview.schema
```

Then, define the SQLite database in the Databases section:

```
[Databases]
    [[archive_sqlite]]
        database_type = SQLite
        database_name = weewx.sdb
```

Now, add the InfluxLoopService to the Engine's service list:

```
[Engine]
    [[Services]]
        # Add the InfluxLoopService to the data_services list
        data_services = user.influxloop.InfluxLoopService
        
        # Other standard services remain unchanged
        prep_services = weewx.engine.StdTimeSynch
        process_services = weewx.engine.StdConvert, weewx.engine.StdCalibrate, weewx.engine.StdQC, weewx.wxservices.StdWXCalculate
        xtype_services = weewx.wxxtypes.StdWXXTypes, weewx.wxxtypes.StdPressureCooker, weewx.wxxtypes.StdRainRater, weewx.wxxtypes.StdDelta
        archive_services = weewx.engine.StdArchive
        restful_services = 
        report_services = weewx.engine.StdPrint, weewx.engine.StdReport
```

Finally, add the configuration for the InfluxLoopService:

```
# InfluxDB Loop Service Configuration
[InfluxLoopService]
    # InfluxDB Connection Settings
    host = localhost
    port = 8086
    org = weewx
    token = YOUR_INFLUXDB_TOKEN
    bucket = weewx_realtime
    measurement = loop
    protocol = http
    
    # Additional configuration options
    # Batch settings (optional)
    batch_size = 50
    batch_timeout = 10000
    
    # Additional tags to include with each measurement (optional)
    # Format: tag1=value1, tag2=value2
    tags = source=weewx
    
    # Skip null/None values
    skip_none = true
    
    # Fields to ignore from LOOP packets (comma-separated)
    ignore_fields = 
    
    # Include station information as tags
    include_station_info = true
    
    # Logging settings
    log_success = false
    log_failure = true
```

### 3. Restart WeeWX

Apply the changes by restarting WeeWX:

```bash
sudo systemctl restart weewx
```

### 4. Verify the Setup

Check the system logs to ensure the service started properly:

```bash
sudo journalctl -u weewx -f
```

You should see log entries indicating that the InfluxLoopService initialized successfully.

### 5. Check Data in InfluxDB

Create a quick script to check if real-time data is being recorded:

```python
#!/usr/bin/env python3
from influxdb_client import InfluxDBClient
import sys

# Connection parameters - update these!
conn_params = {
    'url': 'http://localhost:8086',
    'token': 'YOUR_INFLUXDB_TOKEN_HERE',
    'org': 'weewx',
}

print("Checking real-time data in InfluxDB...")
client = InfluxDBClient(**conn_params)
query_api = client.query_api()

# Query recent data from the loop measurement
query = '''
from(bucket: "weewx_realtime")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "loop")
  |> limit(n: 20)
'''

results = query_api.query(query=query)

if results:
    print(f"Found {len(results)} tables with real-time data")
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
    print("No real-time data found - check your configuration")

client.close()
```

## How It Works

1. **Archive Storage**: WeeWX continues to process and store archive records at the defined archive_interval (typically 5 minutes) in the SQLite database.

2. **LOOP Data Flow**:
   - The weather station sends LOOP packets (real-time readings)
   - WeeWX receives these packets and dispatches NEW_LOOP_PACKET events
   - The InfluxLoopService listens for these events
   - For each LOOP packet, the service:
     - Creates an InfluxDB data point
     - Sets the timestamp to the packet's dateTime
     - Adds configured tags and fields
     - Writes the data to InfluxDB

3. **Data Visualization**:
   - Use Grafana to create dashboards that combine:
     - Long-term trends and historical data from SQLite
     - Real-time, high-resolution data from InfluxDB

## Benefits of This Setup

1. **Optimized Storage**: 
   - SQLite efficiently handles the archived data used for reports and long-term storage
   - InfluxDB efficiently handles high-frequency time-series data for real-time displays

2. **Best of Both Worlds**:
   - Traditional WeeWX reports and features continue to work with the SQLite database
   - Real-time dashboards can show high-resolution data from InfluxDB

3. **Performance**:
   - Each database handles the workload it's best suited for
   - InfluxDB's time-series optimization handles the higher data volume efficiently

## Troubleshooting

If you encounter issues:

1. **Service Not Loading**:
   - Check for errors in the WeeWX log: `sudo journalctl -u weewx`
   - Verify the influxloop.py file permissions: `sudo chmod 644 /usr/share/weewx/user/influxloop.py`
   - Make sure the Python path is correct: `sudo python3 -c "import sys; print(sys.path)"`

2. **No Data in InfluxDB**:
   - Verify InfluxDB is running: `sudo systemctl status influxdb`
   - Check token permissions in InfluxDB
   - Look for errors in the WeeWX logs related to InfluxLoopService

3. **Performance Issues**:
   - Adjust the batch_size and batch_timeout parameters
   - Use a separate InfluxDB bucket for loop data to optimize storage
   - Consider reducing the fields sent to InfluxDB by using the ignore_fields parameter

## Advanced Configuration

### Field Filtering

You can control which fields are sent to InfluxDB by listing unwanted fields in the ignore_fields parameter:

```
ignore_fields = dateTime_raw, usUnits, interval
```

### Tag Customization

Additional fixed tags can provide context for your data:

```
tags = station=home_weather, environment=outdoor
```

### Multiple Stations

For multiple weather stations, you can run multiple instances of WeeWX with different InfluxDB buckets, or use the tags parameter to differentiate data sources:

```
tags = station_id=backyard
```

## Conclusion

This dual-storage approach gives you the best of both worlds: traditional WeeWX functionality with SQLite for archive data, plus high-resolution real-time data in InfluxDB. This configuration is especially valuable for creating responsive dashboards that update in real-time while maintaining efficient long-term storage for historical weather data.