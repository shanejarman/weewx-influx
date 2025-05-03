# WeeWX InfluxDB Integration

This integration allows WeeWX to store weather data in InfluxDB, a purpose-built time-series database.

## Prerequisites

- WeeWX installed and configured
- InfluxDB (v2.x) server installed and running
- Python 3.6 or higher

## Installation

Install the InfluxDB client library:

```shell
pip install influxdb-client
```

## Configuration

### Step 1: Configure InfluxDB

1. Set up an InfluxDB instance if you haven't already
2. Create an organization
3. Create a bucket to store your WeeWX data (e.g., "weewx")
4. Generate an API token with appropriate permissions (read/write to your bucket)

### Step 2: Configure WeeWX to use InfluxDB

Edit your `weewx.conf` file to include the following sections:

```ini
[DatabaseTypes]
    [[InfluxDB]]
        driver = weedb.influx
        host = localhost  # Your InfluxDB host
        port = 8086       # Your InfluxDB port
        protocol = http   # http or https
        org = your_org    # Your InfluxDB organization name
        token = your_token  # Your InfluxDB API token

[Databases]
    [[archive_influxdb]]
        database_type = InfluxDB
        bucket = weewx  # Name of the InfluxDB bucket to use

[DataBindings]
    [[wx_binding]]
        # Use InfluxDB instead of SQLite
        database = archive_influxdb
        # The name of the measurement (InfluxDB doesn't have traditional tables)
        table_name = archive
        # The manager handles aggregation of data for historical summaries
        manager = weewx.manager.DaySummaryManager
        # The schema defines the structure of the database
        # It is *only* used when the database is created
        schema = schemas.wview_extended.schema
```

### Step 3: Restart WeeWX

```shell
sudo /etc/init.d/weewx restart
```

or

```shell
sudo systemctl restart weewx
```

## Data Model in InfluxDB

In InfluxDB, data is organized differently than in traditional SQL databases:

- Each record is stored as a **point** with a timestamp
- Weather observations are stored as **fields**
- Additional metadata can be stored as **tags**
- The `table_name` parameter in WeeWX configuration becomes the **measurement** name in InfluxDB

## Limitations

This integration has some limitations compared to the SQLite and MySQL backends:

1. **Schema Evolution**: InfluxDB is schemaless, so the schema definition is used primarily for initialization
2. **Transactions**: InfluxDB doesn't support transactions in the same way as SQL databases
3. **SQL Compatibility**: InfluxDB uses the Flux query language, not SQL (though limited SQL compatibility exists in newer versions)

## Querying Data

You can query your WeeWX data from InfluxDB using the Flux query language:

```flux
from(bucket: "weewx")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "archive")
  |> filter(fn: (r) => r._field == "outTemp" or r._field == "barometer")
```

## Troubleshooting

### Connection Issues

If you experience connection issues:

1. Verify your InfluxDB server is running
2. Check that the host, port, and protocol are correct
3. Verify your organization name is correct
4. Ensure your token has appropriate permissions for the bucket

### Missing Data

If data is not appearing in InfluxDB:

1. Check WeeWX logs for any errors related to the database
2. Verify the bucket exists in your InfluxDB instance
3. Make sure the token has write permissions to the bucket