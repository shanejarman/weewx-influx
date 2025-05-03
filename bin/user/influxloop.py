#!/usr/bin/env python
"""
Service for sending real-time LOOP data to InfluxDB while maintaining
standard archive records in SQLite.
"""
import sys
import syslog
import time
from datetime import datetime
import weewx
from weewx.engine import StdService

# Import the InfluxDB client
try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    syslog.syslog(syslog.LOG_ERR, "influxloop: requires influxdb-client package")
    raise

# Inherit from the base class StdService
class InfluxLoopService(StdService):
    """Service that sends LOOP data to InfluxDB in real-time."""
    
    def __init__(self, engine, config_dict):
        # Initialize the superclass
        super(InfluxLoopService, self).__init__(engine, config_dict)
        
        # Extract the configuration information for this service
        try:
            service_dict = config_dict['InfluxLoopService']
            
            # Get InfluxDB connection parameters
            self.host = service_dict.get('host', 'localhost')
            self.port = int(service_dict.get('port', 8086))
            self.org = service_dict.get('org', 'weewx')
            self.token = service_dict.get('token', '')
            self.bucket = service_dict.get('bucket', 'weewx_realtime')
            self.measurement = service_dict.get('measurement', 'loop')
            self.protocol = service_dict.get('protocol', 'http')
            
            # Optional batch settings
            self.batch_size = int(service_dict.get('batch_size', 50))
            self.batch_timeout = int(service_dict.get('batch_timeout', 10000))  # in ms
            
            # Tags to add to each measurement
            self.tags = {}
            tags_str = service_dict.get('tags', '')
            if tags_str:
                pairs = [x.strip() for x in tags_str.split(',')]
                for pair in pairs:
                    tag_name, tag_value = [x.strip() for x in pair.split('=')]
                    self.tags[tag_name] = tag_value
                    
            # Skip undefined readings (None values)
            self.skip_none = weeutil.weeutil.to_bool(service_dict.get('skip_none', True))
            
            # Fields to ignore from LOOP packets
            self.ignore_fields = [x.strip() for x in service_dict.get('ignore_fields', '').split(',')]
            
            # Include other useful metadata in readings
            self.include_station_info = weeutil.weeutil.to_bool(service_dict.get('include_station_info', True))
            
            # Debug settings
            self.log_success = weeutil.weeutil.to_bool(service_dict.get('log_success', False))
            self.log_failure = weeutil.weeutil.to_bool(service_dict.get('log_failure', True))
            
            syslog.syslog(syslog.LOG_INFO, "influxloop: InfluxDB LOOP service initialized for %s:%s, bucket=%s" % 
                          (self.host, self.port, self.bucket))
            
        except KeyError as e:
            syslog.syslog(syslog.LOG_ERR, "influxloop: missing configuration key: %s" % e)
            raise
        
        # Initialize the InfluxDB client
        self.client = None
        self.write_api = None
        self.init_client()
        
        # Bind to the NEW_LOOP_PACKET event
        self.bind(weewx.NEW_LOOP_PACKET, self.handle_new_loop_packet)
        
    def init_client(self):
        """Initialize the InfluxDB client connection"""
        try:
            url = f"{self.protocol}://{self.host}:{self.port}"
            self.client = InfluxDBClient(url=url, token=self.token, org=self.org)
            
            # Initialize the write API
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
            syslog.syslog(syslog.LOG_INFO, "influxloop: InfluxDB client initialized")
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, "influxloop: failed to initialize InfluxDB client: %s" % e)
            self.client = None
            self.write_api = None
    
    def handle_new_loop_packet(self, event):
        """Handle loop packets by sending them to InfluxDB"""
        if self.client is None or self.write_api is None:
            # Try to reinitialize client
            self.init_client()
            if self.client is None or self.write_api is None:
                return
                
        try:
            # Extract the packet data
            packet = event.packet
            
            # Create a data point
            point = Point(self.measurement)
            
            # Add timestamp from the packet if available, otherwise use current time
            if 'dateTime' in packet:
                timestamp = datetime.utcfromtimestamp(packet['dateTime'])
                point = point.time(timestamp)
            
            # Add tags
            for tag_name, tag_value in self.tags.items():
                point = point.tag(tag_name, tag_value)
                
            # Add fields from the packet
            fields_added = 0
            
            for key, value in packet.items():
                # Skip None values if configured to do so
                if value is None and self.skip_none:
                    continue
                    
                # Skip fields in the ignore list
                if key in self.ignore_fields:
                    continue
                    
                # Handle specific metadata fields as tags
                if key in ('usUnits', 'interval'):
                    # Add as tag
                    point = point.tag(key, str(value))
                    continue
                    
                # Add all other values as fields
                try:
                    if key != 'dateTime':  # Already handled as timestamp
                        point = point.field(key, value)
                        fields_added += 1
                except Exception as e:
                    syslog.syslog(syslog.LOG_ERR, 
                                  "influxloop: cannot add field %s with value %s: %s" % 
                                  (key, value, e))
                    
            # Add station info as tags if configured
            if self.include_station_info:
                # Get station info from config
                station_dict = self.engine.stn_info.as_dict()
                for key, value in station_dict.items():
                    if key in ('altitude_m', 'latitude', 'longitude', 'location', 'station_type'):
                        point = point.tag(key, str(value))
            
            # Only send if we have fields to add
            if fields_added > 0:
                # Write the data point to InfluxDB
                self.write_api.write(bucket=self.bucket, org=self.org, record=point)
                
                if self.log_success:
                    syslog.syslog(syslog.LOG_DEBUG, 
                                  "influxloop: wrote %s fields to InfluxDB at %s" % 
                                  (fields_added, timestamp if 'dateTime' in packet else 'current time'))
                
        except Exception as e:
            if self.log_failure:
                syslog.syslog(syslog.LOG_ERR, "influxloop: failed to write LOOP data: %s" % e)
            
    def shutDown(self):
        """Close InfluxDB connection when service shuts down"""
        try:
            if self.write_api:
                self.write_api.close()
            if self.client:
                self.client.close()
                syslog.syslog(syslog.LOG_INFO, "influxloop: InfluxDB client closed")
        except Exception:
            pass

# To test this module, you can add a basic unit test
if __name__ == "__main__":
    import unittest
    
    class TestInfluxLoopService(unittest.TestCase):
        def test_basic_initialization(self):
            """Test that the service can be initialized with minimal config"""
            import configobj
            config = configobj.ConfigObj({
                'InfluxLoopService': {
                    'host': 'localhost',
                    'port': 8086,
                    'token': 'test_token',
                    'org': 'test_org',
                    'bucket': 'test_bucket'
                }
            })
            
            # Create a mock engine
            engine = type('MockEngine', (), {})()
            engine.stn_info = type('MockStationInfo', (), {})()
            engine.stn_info.as_dict = lambda: {
                'altitude_m': 100,
                'latitude': 35.5,
                'longitude': -80.2,
                'location': 'Test Location',
                'station_type': 'TestStation'
            }
            
            # Disable actual service initialization by mocking the bind method
            engine.bind = lambda event, callback: None
            
            # Import weeutil for the mock
            import weeutil.weeutil
            
            # Initialize service (this should not raise exceptions)
            service = InfluxLoopService(engine, config)
            
            # Verify service has correct configuration
            self.assertEqual(service.host, 'localhost')
            self.assertEqual(service.port, 8086)
            self.assertEqual(service.bucket, 'test_bucket')
            
    unittest.main()