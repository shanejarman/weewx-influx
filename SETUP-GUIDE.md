# Setting Up WeeWX with InfluxDB on Raspberry Pi

This guide will walk you through the complete process of setting up WeeWX with InfluxDB on a Raspberry Pi, from initial installation to configuration and running as a service.

## 1. Prerequisites

- Raspberry Pi (3 or newer recommended) with Raspberry Pi OS installed
- Internet connection
- Weather station compatible with WeeWX
- Basic familiarity with Linux terminal commands

## 2. Install InfluxDB

First, we'll install and configure InfluxDB v2.x:

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install required dependencies
sudo apt install -y gnupg2 curl wget

# Add InfluxData repository GPG key
wget -qO- https://repos.influxdata.com/influxdb.key | gpg --dearmor > influxdb.gpg
sudo mv influxdb.gpg /etc/apt/trusted.gpg.d/influxdb.gpg

# Add the repository
export DISTRIB_ID=$(lsb_release -si)
export DISTRIB_CODENAME=$(lsb_release -sc)
echo "deb [signed-by=/etc/apt/trusted.gpg.d/influxdb.gpg] https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/influxdb.list

# Update package list and install InfluxDB
sudo apt update
sudo apt install -y influxdb2
```

## 3. Configure InfluxDB

Now, start InfluxDB and perform initial setup:

```bash
# Start InfluxDB service
sudo systemctl enable influxdb
sudo systemctl start influxdb

# Check if the service is running
sudo systemctl status influxdb
```

Next, set up InfluxDB with the web interface or CLI:

### Using the Web Interface

1. Open a browser and navigate to `http://your-raspberry-pi-ip:8086`
2. Follow the setup wizard to:
   - Create an initial admin user
   - Create an organization (e.g., "weewx")
   - Create your first bucket (e.g., "weather_data")
   - Copy your API token when shown (save it somewhere secure)

### Using the CLI

```bash
# Initial setup with CLI
influx setup \
  --username admin \
  --password YourSecurePassword123 \
  --org weewx \
  --bucket weather_data \
  --retention 0 \
  --force

# Get and save your token
TOKEN=$(influx auth list --user admin --json | grep token | cut -d '"' -f4)
echo "Your token is: $TOKEN"
echo "Save this token in a secure place!"
```

## 4. Install WeeWX

Install WeeWX using the recommended method for Raspberry Pi:

```bash
# Add the weewx repository
wget -qO - https://weewx.com/keys.html | sudo gpg --dearmor --output /etc/apt/trusted.gpg.d/weewx.gpg
echo "deb [arch=all] https://weewx.com/apt/python3 buster main" | sudo tee /etc/apt/sources.list.d/weewx.list

# Update and install weewx
sudo apt update
sudo apt install -y weewx
```

## 5. Install Python Dependencies for InfluxDB Integration

WeeWX needs the InfluxDB client library:

```bash
# Create and activate a virtual environment for WeeWX (recommended)
sudo python3 -m venv /usr/share/weewx/influx_venv
sudo /usr/share/weewx/influx_venv/bin/pip install influxdb-client
```

## 6. Configure WeeWX for InfluxDB

Create a custom WeeWX configuration:

```bash
# Make a backup of the original config
sudo cp /etc/weewx/weewx.conf /etc/weewx/weewx.conf.original

# Create a new weewx-influxdb.conf
sudo nano /etc/weewx/weewx-influxdb.conf
```

Paste the following configuration, modifying it for your setup:

```ini
# WEEWX CONFIGURATION FILE for InfluxDB
#
# This is a modified version of the standard weewx.conf
# configured to use your weather station driver and InfluxDB backend

##############################################################################

# This section is for general configuration information.

# Set to 1 for extra debug info, otherwise comment it out or set to zero.
debug = 0

# Whether to log successful operations
log_success = True

# Whether to log unsuccessful operations
log_failure = True

##############################################################################

#   This section is for information about the station.

[Station]
    
    # Description of the station location
    location = Your Station Location
    
    # Latitude and longitude for reports
    latitude = 0.0
    longitude = 0.0
    
    # Altitude of the station
    altitude = 0, meter
    
    # Set to use your appropriate driver
    station_type = YOUR_STATION_TYPE
    
    # Rain year start month
    rain_year_start = 1
    
    # Start of week (0=Monday, 6=Sunday)
    week_start = 6

##############################################################################

# Driver-specific section - modify based on your weather station
[YOUR_STATION_TYPE]
    # Configuration goes here - check WeeWX docs for your specific station
    driver = weewx.drivers.your_station_driver
    # Add other station-specific parameters

##############################################################################

#   This section is for configuring the archive service

[StdArchive]
    
    # Archive interval in seconds (5 minutes)
    archive_interval = 300
    
    # Generate archive records in software
    record_generation = software
    
    # Include LOOP data in hi/low statistics
    loop_hilo = True
    
    # The data binding used to save archive records
    data_binding = wx_binding

##############################################################################

#   This section binds a data store to a database

[DataBindings]
    
    [[wx_binding]]
        # Use our InfluxDB database
        database = influx_archive
        # The measurement name in InfluxDB
        table_name = archive
        # The manager handles aggregation of data for historical summaries
        manager = weewx.manager.DaySummaryManager
        # The schema defines the structure of the database
        schema = schemas.wview.schema

##############################################################################

#   This section defines various databases

[Databases]
    
    # InfluxDB configuration
    [[influx_archive]]
        database_type = InfluxDB
        host = localhost
        port = 8086
        org = weewx
        token = YOUR_INFLUXDB_TOKEN_HERE
        bucket = weather_data
        driver = weedb.influx

##############################################################################

#   This section defines defaults for the different types of databases

[DatabaseTypes]
    
    # Defaults for InfluxDB databases
    [[InfluxDB]]
        driver = weedb.influx
        host = localhost
        port = 8086

##############################################################################

#   This section configures the internal weewx engine

[Engine]
    
    # This section specifies which services should be run and in what order
    [[Services]]
        prep_services = weewx.engine.StdTimeSynch
        data_services = ,
        process_services = weewx.engine.StdConvert, weewx.engine.StdCalibrate, weewx.engine.StdQC, weewx.wxservices.StdWXCalculate
        xtype_services = weewx.wxxtypes.StdWXXTypes, weewx.wxxtypes.StdPressureCooker, weewx.wxxtypes.StdRainRater, weewx.wxxtypes.StdDelta
        archive_services = weewx.engine.StdArchive
        restful_services = 
        report_services = weewx.engine.StdPrint, weewx.engine.StdReport
```

Replace these values with your specific details:
- `YOUR_STATION_TYPE`: Your weather station model (e.g., Vantage, FineOffsetUSB)
- `weewx.drivers.your_station_driver`: Appropriate driver for your station
- `YOUR_INFLUXDB_TOKEN_HERE`: The token you saved during InfluxDB setup

## 7. Install the InfluxDB Module for WeeWX

Copy the InfluxDB integration module into the WeeWX installation:

```bash
# Create if it doesn't exist
sudo mkdir -p /usr/share/weewx/weedb
```

Create the influx.py module:

```bash
sudo nano /usr/share/weewx/weedb/influx.py
```

Paste the contents of your InfluxDB module (the file at src/weedb/influx.py in your repo).

## 8. Configure WeeWX to Use the Virtual Environment

Edit the WeeWX startup script to use the virtual environment:

```bash
sudo nano /etc/systemd/system/weewx.service
```

Modify the ExecStart line to look like this:

```
ExecStart=/usr/share/weewx/influx_venv/bin/python3 /usr/bin/weewxd /etc/weewx/weewx-influxdb.conf
```

## 9. Start and Monitor WeeWX

Finally, reload the systemd configuration and restart WeeWX:

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable and start WeeWX
sudo systemctl enable weewx
sudo systemctl restart weewx

# Check the status
sudo systemctl status weewx

# Monitor the logs
sudo journalctl -f -u weewx
```

## 10. Verify Data in InfluxDB

Create a quick test script to check if data is being recorded:

```bash
nano ~/check_influx_data.py
```

Paste this script (adjusting the token and other parameters):

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

print("Checking data in InfluxDB...")
client = InfluxDBClient(**conn_params)
query_api = client.query_api()

# Query recent data
query = '''
from(bucket: "weather_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "archive")
  |> limit(n: 10)
'''

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
    print("No data found - check your configuration")

client.close()
```

Run the script:

```bash
chmod +x ~/check_influx_data.py
~/check_influx_data.py
```

## 11. Set Up Grafana for Visualization (Optional)

To visualize your weather data:

```bash
# Install Grafana
sudo apt-get install -y software-properties-common
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install -y grafana

# Start and enable Grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

Access Grafana at `http://your-raspberry-pi-ip:3000` (default username/password: admin/admin).

1. Add a data source: Select InfluxDB, use the Flux query language option
2. Configure the connection:
   - URL: http://localhost:8086
   - Organization: weewx
   - Token: Your InfluxDB token
   - Default bucket: weather_data
3. Create dashboards using the data from your weather station

## 12. Troubleshooting

If you encounter issues:

1. Check WeeWX logs: `sudo journalctl -u weewx`
2. Verify InfluxDB is running: `sudo systemctl status influxdb`
3. Test InfluxDB connectivity: `curl http://localhost:8086/ping -v`
4. Ensure the token has appropriate permissions in InfluxDB
5. Check for Python errors: Look for import errors related to the influxdb_client module

Common fixes:
- Reinstall the influxdb-client: `sudo /usr/share/weewx/influx_venv/bin/pip install --upgrade influxdb-client`
- Check permissions: `sudo chown -R weewx:weewx /usr/share/weewx/influx_venv`
- Restart services: `sudo systemctl restart influxdb weewx`

## 13. Maintenance

For ongoing maintenance:

1. Backup your configuration regularly:
   ```bash
   sudo cp /etc/weewx/weewx-influxdb.conf /etc/weewx/weewx-influxdb.conf.backup
   ```

2. Check for updates:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

3. Monitor disk space:
   ```bash
   df -h
   ```

4. Consider setting up InfluxDB retention policies if your storage is limited

## Conclusion

You now have WeeWX running on your Raspberry Pi with data being stored in InfluxDB. This modern setup gives you the benefits of a time-series database designed for sensor data, along with the ability to create beautiful visualizations using tools like Grafana.

For more information, refer to:
- [WeeWX Documentation](http://weewx.com/docs.html)
- [InfluxDB Documentation](https://docs.influxdata.com/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)