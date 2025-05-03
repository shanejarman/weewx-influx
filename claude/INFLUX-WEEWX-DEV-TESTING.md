# WeeWX InfluxDB Development Testing Guide

This guide provides step-by-step instructions for testing the WeeWX InfluxDB integration during development.

## Prerequisites

1. A working WeeWX installation
2. A running InfluxDB v2.x server
3. The influxdb-client Python package installed:
   ```bash
   pip install influxdb-client
   ```
4. Basic knowledge of WeeWX configuration

## Method 1: Using the Simulator Driver

The simulator driver generates synthetic weather data that can be used to test the entire data flow from generation to storage.

### Step 1: Configure WeeWX to use the simulator

Edit your `weewx.conf` file to use the simulator driver:

```ini
[Station]
    station_type = simulator
    
[Simulator]
    driver = weewx.drivers.simulator
    mode = simulator
    # Set to 'generator' for accelerated data generation
    # mode = generator
```

### Step 2: Configure InfluxDB as the database

Add or modify the database configuration section to use InfluxDB:

```ini
[DataBindings]
    [[wx_binding]]
        database = influx_archive
        manager = weewx.manager.DaySummaryManager
        table_name = archive
        schema = schemas.wview.schema

[Databases]
    [[influx_archive]]
        database_type = influxdb
        host = localhost
        port = 8086
        org = your_organization
        token = your_api_token
        bucket = weewx_archive
```

Replace `your_organization` and `your_api_token` with your actual InfluxDB organization and API token.

### Step 3: Run WeeWX

Start WeeWX to begin generating simulated data and storing it in InfluxDB:

```bash
weewxd /path/to/weewx.conf
```

Monitor the WeeWX log file for any errors or issues with the InfluxDB connection.

### Step 4: Verify Data in InfluxDB

Use the InfluxDB UI or API to verify that data is being received:

```bash
# Using the InfluxDB CLI
influx query 'from(bucket: "weewx_archive") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "archive")'
```

## Method 2: Testing the Database Driver Directly

You can test the InfluxDB driver directly by creating a unit test based on the existing WeeWX database tests.

### Step 1: Create a test file for InfluxDB

Create a new file `test_influx.py` in the `src/weedb/tests/` directory:

```python
import unittest
import weedb
from weedb.tests.test_weedb import Common

class TestInflux(Common, unittest.TestCase):
    """Test the InfluxDB interface."""
    
    def setUp(self):
        """Set up the test environment."""
        self.db_dict = {
            'database_type': 'influxdb',
            'host': 'localhost',
            'port': 8086,
            'org': 'your_organization',
            'token': 'your_api_token',
            'bucket': 'weewx_test'
        }
        # Drop the test database if it exists:
        try:
            weedb.drop(self.db_dict)
        except:
            pass
        # Create the test database:
        weedb.create(self.db_dict)

    def tearDown(self):
        """Remove the test database."""
        try:
            weedb.drop(self.db_dict)
        except:
            pass

if __name__ == '__main__':
    unittest.main()
```

Replace `your_organization` and `your_api_token` with your actual InfluxDB credentials.

### Step 2: Run the tests

Execute the test script:

```bash
python -m weedb.tests.test_influx
```

## Method 3: Using gen_fake_data.py for Controlled Testing

The `gen_fake_data.py` script can generate a complete synthetic database with predictable values, which is useful for testing reports and queries.

### Step 1: Modify gen_fake_data.py to work with InfluxDB

Copy and adapt the `gen_fake_data.py` script to work with InfluxDB:

```bash
cp src/weewx/tests/gen_fake_data.py src/weewx/tests/gen_fake_influx_data.py
```

Edit `gen_fake_influx_data.py` to adjust the database configuration for InfluxDB.

### Step 2: Generate test data

Run the modified script:

```bash
python -m weewx.tests.gen_fake_influx_data
```

### Step 3: Verify the generated data

Use InfluxDB's tools to query and verify the generated data:

```bash
influx query 'from(bucket: "weewx_test") |> range(start: 2010-01-01T00:00:00Z, stop: 2010-10-01T00:00:00Z) |> filter(fn: (r) => r._measurement == "archive")'
```

## Debugging Tips

1. Enable DEBUG level logging in WeeWX by adding to `weewx.conf`:
   ```ini
   [Logging]
       [[loggers]]
           [[[root]]]
               level = DEBUG
   ```

2. Check the InfluxDB logs for any server-side issues.

3. Use the InfluxDB UI to monitor data ingestion and query performance.

4. If you encounter issues with SQL translation to Flux (InfluxDB's query language), you may need to modify the query handling in `influx.py`.

## Common Issues and Solutions

1. **Connection Errors**: Verify your InfluxDB server is running and accessible, and that your token has the necessary permissions.

2. **Data Type Mismatches**: InfluxDB handles data types differently than SQL databases. Watch for issues with field types in your queries.

3. **Query Translation**: Complex SQL queries may not translate cleanly to Flux. You might need to enhance the query translation logic.

4. **Performance Issues**: If you encounter slow performance, check your InfluxDB configuration, particularly memory allocation and indexing.

## Next Steps

After basic testing confirms that your InfluxDB integration works with simple data flows, consider testing:

1. Historical data imports (using `weectl import`)
2. Report generation with InfluxDB as the data source
3. Data aggregation performance
4. Advanced queries used by WeeWX's reporting engine

By systematically testing these aspects, you can ensure your InfluxDB integration is robust and ready for production use.