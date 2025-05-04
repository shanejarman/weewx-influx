# Docker Setup for InfluxDB on Raspberry Pi

This guide provides instructions for installing Docker on your Raspberry Pi and running InfluxDB using Docker Compose.

## Installing Docker on Raspberry Pi

1. Update your Raspberry Pi:
```bash
sudo apt update
sudo apt upgrade -y
```

2. Install Docker using the convenience script:
```bash
curl -sSL https://get.docker.com | sh
```

3. Add your user to the Docker group to run Docker without sudo:
```bash
sudo usermod -aG docker $USER
```

4. Log out and log back in for the group changes to take effect, or run:
```bash
newgrp docker
```

5. Install Docker Compose:
```bash
sudo apt install -y docker-compose-plugin
```

6. Verify Docker is working:
```bash
docker --version
docker compose version
```

## Setting Up Your Docker Compose for InfluxDB

1. Create a directory for your compose file:
```bash
mkdir -p ~/docker/influxdb
cd ~/docker/influxdb
```

2. Create a `docker-compose.yml` file:
```bash
nano docker-compose.yml
```

3. Add your configuration to the file:
```yaml
version: '3'
services:
  influxdb:
    image: influxdb:latest
    container_name: influxdb
    ports:
      - "8086:8086"
    volumes:
      - influxdb-data:/var/lib/influxdb2
      - influxdb-config:/etc/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=your_password
      - DOCKER_INFLUXDB_INIT_ORG=weewx
      - DOCKER_INFLUXDB_INIT_BUCKET=weather_data
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=your_secret_token
    restart: unless-stopped

volumes:
  influxdb-data:
  influxdb-config:
```

4. Start the InfluxDB container:
```bash
docker compose up -d
```

5. Verify InfluxDB is running:
```bash
docker ps
```

## Verifying InfluxDB is Working

You can verify InfluxDB is running correctly using several methods:

### Method 1: Check the container logs
```bash
docker logs influxdb-influxdb-1
```
Look for messages indicating the server started successfully like "Listening on...".

### Method 2: Access the web interface
Open a browser and go to `http://<your-pi-ip>:8086`. You should see the InfluxDB login page.

### Method 3: Use the InfluxDB CLI

#### Checking if your Raspberry Pi is 32-bit or 64-bit

Before installing the CLI, check which architecture your Raspberry Pi is running:

```bash
# Check architecture
uname -m
```

If the result is:
- `aarch64` or `arm64`: You have a 64-bit system
- `armv7l` or `armv6l`: You have a 32-bit system

You can also check the OS architecture:
```bash
# Check OS (not just CPU)
getconf LONG_BIT
```
This will return either `32` or `64` depending on your OS.

#### Installing the appropriate InfluxDB CLI

```bash
# Option 1: For 64-bit Raspberry Pi (if uname -m shows aarch64/arm64)
wget https://dl.influxdata.com/influxdb/releases/influxdb2-client-2.7.3-linux-arm64.tar.gz
tar xvzf influxdb2-client-2.7.3-linux-arm64.tar.gz
# Find the influx binary (directory structure might vary)
find . -name "influx" -type f
# After finding it, copy it to the right location
# For example, if found in ./influx:
sudo cp ./influx /usr/local/bin/
sudo chmod +x /usr/local/bin/influx

# Option 2: For 32-bit Raspberry Pi (if uname -m shows armv7l/armv6l)
wget https://dl.influxdata.com/influxdb/releases/influxdb2-client-2.7.3-linux-armhf.tar.gz
tar xvzf influxdb2-client-2.7.3-linux-armhf.tar.gz
# Find the influx binary (directory structure might vary)
find . -name "influx" -type f
# After finding it, copy it to the right location
# For example, if found in ./influx:
sudo cp ./influx /usr/local/bin/
sudo chmod +x /usr/local/bin/influx

# Check if CLI works
influx version

# Query InfluxDB status
influx ping --host http://localhost:8086
```

### Method 4: Run a query with curl
```bash
# Replace YOUR_TOKEN with your actual token
curl -G "http://localhost:8086/api/v2/query?org=weewx" \
  --header "Authorization: Token your_secret_token" \
  --header "Content-Type: application/vnd.flux" \
  --data-urlencode "query=from(bucket:\"weather_data\") |> range(start: -1h) |> limit(n:5)"
```

### Method 5: Create a simple test script
Create a file named `test_influx.py`:
```python
from influxdb_client import InfluxDBClient

# Replace with your actual token
token = "YOUR_TOKEN"
org = "weewx"
url = "http://localhost:8086"

client = InfluxDBClient(url=url, token=token, org=org)

# Test the connection
health = client.health()
print(f"InfluxDB Status: {health.status}")
print(f"Version: {health.version}")

# Get available buckets
buckets_api = client.buckets_api()
buckets = buckets_api.find_buckets().buckets
print("\nAvailable buckets:")
for bucket in buckets:
    print(f" - {bucket.name}")

client.close()
```

Run the script:
```bash
pip install influxdb-client
python3 test_influx.py
```

## Configuring WeeWX to Use InfluxDB

1. Update your WeeWX configuration (`/etc/weewx/weewx.conf`) with these settings:
```ini
[DatabaseTypes]
    [[InfluxDB]]
        driver = weedb.influx
        host = localhost
        port = 8086
        protocol = http
        org = weewx
        token = your_token

[Databases]
    [[archive_influxdb]]
        database_type = InfluxDB
        bucket = weather_data

[DataBindings]
    [[wx_binding]]
        database = archive_influxdb
        table_name = archive
        manager = weewx.manager.DaySummaryManager
        schema = schemas.wview_extended.schema
```

This Docker Compose setup will get InfluxDB up and running properly on your Raspberry Pi. The configuration includes:
- Latest InfluxDB image
- Persistent storage for data and config
- Initial setup with admin user, organization, and bucket
- Automatic restart if your Pi reboots
- Exposed on port 8086

Remember to replace `your_password` and `your_token` with secure values.