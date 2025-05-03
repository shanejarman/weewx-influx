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

## 4. Install WeeWX with InfluxDB Support

Instead of installing the standard WeeWX package, we'll install the forked version that includes InfluxDB integration:

```bash
# Install Git and required build dependencies
sudo apt update
sudo apt install -y git python3-pip python3-dev python3-venv

# Create a directory for WeeWX
mkdir -p ~/weewx-influx
cd ~/weewx-influx

# Clone the forked repository with InfluxDB support
git clone https://github.com/shanejarman/weewx-influx.git .

# Create a virtual environment
python3 -m venv weewx-venv
source weewx-venv/bin/activate

# Install dependencies using Poetry (recommended method)
# Install Poetry if you don't have it
pip install poetry

# Disable keyring to prevent hanging during installation
poetry config keyring.enabled false

# Install project dependencies using Poetry
poetry install

# Alternatively, you can install dependencies directly:
# Install the required influxdb-client package
pip install influxdb-client

# Install other required dependencies (from pyproject.toml)
pip install configobj CT3 Pillow ephem PyMySQL pyserial pyusb importlib-resources

# Install the WeeWX package in development mode
pip install -e .

# Deactivate the virtual environment when done
deactivate
```

### Creating a WeeWX Configuration

```bash
# Create a configuration directory if installing from source
sudo mkdir -p /etc/weewx
sudo cp ~/weewx-influx/weewx-influxdb-test.conf /etc/weewx/weewx.conf

# Edit the configuration file with your settings
sudo nano /etc/weewx/weewx.conf
```

### Set Up WeeWX as a Service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/weewx.service
```

Add the following content:

```
[Unit]
Description=WeeWX weather system
After=network.target

[Service]
Type=simple
ExecStart=/home/pi/weewx-influx/weewx-venv/bin/python3 /home/pi/weewx-influx/bin/weewxd /etc/weewx/weewx.conf
User=pi
Group=pi
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable weewx
sudo systemctl start weewx
```

Check the status:

```bash
sudo systemctl status weewx
```

## 5. Configure WeeWX for Your Weather Station

With the forked version installed, you'll need to update the configuration file for your specific weather station hardware:

```bash
sudo nano /etc/weewx/weewx.conf
```

Edit the following sections to match your setup:

1. Station information:
```ini
[Station]
    # Description of the station location
    location = Your Actual Location
    
    # Latitude and longitude for reports
    latitude = XX.XXXX
    longitude = XX.XXXX
    
    # Altitude of the station
    altitude = XXX, meter
    
    # Set to use your appropriate driver
    station_type = YOUR_STATION_TYPE
```

2. Driver configuration:
```ini
[YOUR_STATION_TYPE]
    # Configuration goes here - check WeeWX docs for your specific station
    driver = weewx.drivers.your_station_driver
    # Add other station-specific parameters
```

3. InfluxDB configuration:
```ini
[Databases]
    [[influx_archive]]
        database_type = InfluxDB
        host = localhost  # Use localhost if InfluxDB is on the same machine
        port = 8086
        org = weewx  # Match the org name you used when setting up InfluxDB
        token = YOUR_INFLUXDB_TOKEN_HERE
        bucket = weather_data
        driver = weedb.influx
```

Replace these values with your specific details:
- `YOUR_STATION_TYPE`: Your weather station model (e.g., Vantage, FineOffsetUSB)
- `weewx.drivers.your_station_driver`: Appropriate driver for your station
- `YOUR_INFLUXDB_TOKEN_HERE`: The token you saved during InfluxDB setup

## 6. Start and Monitor WeeWX

If you haven't already started the WeeWX service:

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

## 7. Verify Data in InfluxDB

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

## 8. Set Up Grafana for Visualization (Optional)

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

## 9. Troubleshooting

If you encounter issues:

1. Check WeeWX logs: `sudo journalctl -u weewx`
2. Verify InfluxDB is running: `sudo systemctl status influxdb` or `docker ps` if using Docker
3. Test InfluxDB connectivity: `curl http://localhost:8086/ping -v`
4. Ensure the token has appropriate permissions in InfluxDB
5. Check for Python errors: Look for import errors related to dependencies

Common fixes:
- Check that Poetry is properly installed and configured: `poetry --version`
- If Poetry hangs on keyring check: `poetry config keyring.enabled false`
- Reinstall dependencies using Poetry: `poetry install`
- Reinstall the influxdb-client: `pip install --upgrade influxdb-client` in your virtual environment
- Check permissions on your data directories
- Restart services: `sudo systemctl restart weewx` and restart InfluxDB (Docker or systemd)

## 10. Maintenance

For ongoing maintenance:

1. Backup your configuration regularly:
   ```bash
   sudo cp /etc/weewx/weewx.conf /etc/weewx/weewx.conf.backup
   ```

2. Keep your system updated:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

3. Monitor disk space:
   ```bash
   df -h
   ```

4. Consider setting up InfluxDB retention policies if your storage is limited

## 11. Updating Your WeeWX Installation During Development

As the WeeWX-InfluxDB integration is being developed and improved, you'll likely need to update your installation regularly. Here's how to pull the latest changes and update your installation:

### Basic Update Process

```bash
# Navigate to your WeeWX installation directory
cd ~/weewx-influx

# Stop the WeeWX service
sudo systemctl stop weewx

# Backup your configuration
sudo cp /etc/weewx/weewx.conf /etc/weewx/weewx.conf.$(date +%Y%m%d)

# Get the latest changes from GitHub
git fetch origin
git pull origin master  # or whatever branch you're tracking

# Activate your virtual environment
source weewx-venv/bin/activate

# Reinstall with the latest changes using Poetry (recommended)
poetry install

# Or alternatively using pip
pip install -e .

# Deactivate the virtual environment
deactivate

# Start WeeWX service
sudo systemctl start weewx

# Check the logs to ensure it started properly
sudo journalctl -n 50 -u weewx
```

### Handling Local Changes

If you've made local changes to the code that you want to preserve:

```bash
# Stash your changes before pulling
git stash

# Pull the latest changes
git pull origin master

# Re-apply your changes
git stash pop

# If there are merge conflicts, you'll need to resolve them
# After resolving conflicts, continue with the installation
```

### Switching Branches for Testing

If you want to test a specific branch or feature:

```bash
# Check available branches
git branch -a

# Switch to a specific branch
git checkout branch-name

# Update and restart
source weewx-venv/bin/activate
# Install using Poetry (recommended)
poetry install
# Or alternatively using pip
# pip install -e .
deactivate
sudo systemctl restart weewx
```

### Debugging Tips

1. Check WeeWX logs for errors:
   ```bash
   sudo journalctl -f -u weewx
   ```

2. Increase debug level in `weewx.conf`:
   ```ini
   debug = 1
   ```

3. Test a single run without the service:
   ```bash
   # Stop the service
   sudo systemctl stop weewx
   
   # Run manually with debug output
   cd ~/weewx-influx
   source weewx-venv/bin/activate
   python bin/weewxd --debug /etc/weewx/weewx.conf
   deactivate
   
   # Restart the service when done
   sudo systemctl start weewx
   ```

4. Check data flow to InfluxDB:
   ```bash
   # Run the check script after making changes
   ~/check_influx_data.py
   ```

### Reverting to a Known Working Version

If an update causes problems, you can revert to a known working commit:

```bash
# Find the commit hash of the last known working version
git log --oneline

# Revert to that specific commit
git checkout <commit-hash>

# Reinstall that version
source weewx-venv/bin/activate
# Install using Poetry (recommended)
poetry install
# Or alternatively using pip
# pip install -e .
deactivate
sudo systemctl restart weewx
```

Remember to always back up your configuration before making changes, and consider creating a test environment if you're making significant modifications.

## Conclusion

You now have WeeWX running on your Raspberry Pi with data being stored in InfluxDB. This modern setup gives you the benefits of a time-series database designed for sensor data, along with the ability to create beautiful visualizations using tools like Grafana.

As the WeeWX-InfluxDB integration continues to be developed, you can easily keep up with improvements by following the update procedures in this guide.

For more information, refer to:
- [WeeWX Documentation](http://weewx.com/docs.html)
- [InfluxDB Documentation](https://docs.influxdata.com/)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)