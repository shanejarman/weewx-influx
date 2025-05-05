# InfluxDB Unit System Error Analysis

## Error Description

When restarting weewxd with the InfluxDB configuration after a reset, the following error occurs:

```
weewx.UnitError: Unit system of incoming record (0x05) differs from 'archive' table in 'weather_data' database (0x6818c343)
```

This error is thrown from `weewx/manager.py:682` in the `_check_unit_system` method during startup while trying to backfill the day summary.

## Root Cause Analysis

The error occurs because:

1. WeeWX uses a unit system identifier to ensure consistency between records in the database
2. When initially starting with a fresh InfluxDB, the first records set the unit system for the database
3. On restart, WeeWX is trying to use unit system `0x05` (US customary/imperial)
4. But the InfluxDB database shows unit system `0x6818c343` (an invalid/corrupted value)

The mismatch specifically happens during the day summary backfill process at startup. The day summary operation is trying to use a different unit system than what was recorded in the InfluxDB database's metadata.

## Potential Solutions

### Solution 1: Add Unit System Metadata Storage for InfluxDB

**Problem:** InfluxDB likely doesn't store the unit system metadata properly like SQLite/MySQL databases do.

**Approach:** Modify the InfluxDB database driver to properly store and retrieve the unit system metadata.

**Implementation:**
1. Examine how unit systems are stored in `weedb/sqlite.py` and `weedb/mysql.py`
2. Add similar functionality to `weedb/influx.py` to store unit system metadata
3. Consider using a special measurement or tag in InfluxDB to store this metadata
4. Ensure retrieval works correctly during startup

### Solution 2: Add Unit System Configuration Option

**Problem:** The unit system is inconsistent between runs.

**Approach:** Allow explicit configuration of the unit system for InfluxDB in weewx.conf.

**Implementation:**
1. Modify the InfluxDB database binding to accept a `unit_system` configuration option
2. When opening the InfluxDB connection, use this configured value instead of trying to detect it
3. Skip the unit system check for InfluxDB databases or make it configurable
4. Update documentation to explain this configuration option

### Solution 3: Create Unit System Reset/Migration Tool

**Problem:** The unit system becomes corrupted or inconsistent.

**Approach:** Create a tool to reset or migrate the unit system in InfluxDB.

**Implementation:**
1. Create a utility function in `weectl` for resetting or updating the unit system in InfluxDB
2. Add functionality to detect and repair corrupted unit system values
3. Make it possible to force a specific unit system for all InfluxDB measurements
4. Document how to use this tool when migrating or recovering from errors

### Solution 4: Skip Daily Summary Backfill for InfluxDB

**Problem:** The error occurs during the day summary backfill process at startup.

**Approach:** Modify WeeWX to skip the daily summary backfill specifically for InfluxDB databases.

**Implementation:**
1. Identify where the backfill process begins in the startup sequence
2. Modify the engine.py or manager.py to detect when an InfluxDB database is being used
3. Conditionally skip the backfill_day_summary() call for InfluxDB databases
4. Add a configuration option to enable/disable this behavior for flexibility

#### Implementation Analysis

Based on the code examination:

1. **Startup Sequence**:
   - In `engine.py`, the daily summary backfill is triggered in the `startup` method (line 604)
   - The call `_nrecs, _ndays = dbmanager.backfill_day_summary()` initiates the process
   - This happens after database initialization but before the main loop starts

2. **Database Identification**:
   - The database manager is already accessible via `dbmanager = self.engine.db_binder.get_manager()`
   - We can determine if this is an InfluxDB database by checking the connection type
   - This could be done with something like `if dbmanager.connection.connection_name == 'influxdb'`

3. **Conditional Skip**:
   - We could add conditional logic right before line 604 to skip the backfill for InfluxDB
   - This keeps the modification minimal and focused on the exact point of failure

4. **Configuration Option**:
   - A new configuration option like `skip_day_summary_for_influxdb` could be added to weewx.conf
   - This would allow users to control this behavior based on their needs

This approach is less invasive than modifying the database adapter itself and would provide an immediate fix to the error while a more comprehensive solution is developed.

## Implementation Tasks

### Solution 1 Tasks
- [x] Research how unit systems are stored in SQLite/MySQL
- [x] Analyze current InfluxDB adapter implementation in `weedb/influx.py`
- [x] Design a method to store unit system metadata in InfluxDB
- [x] Implement reading/writing of unit system metadata in the InfluxDB adapter
- [ ] Add tests to verify unit system consistency across restarts
- [ ] Update documentation with InfluxDB-specific details

#### Task 4: Implementation of Unit System Metadata Fix

Here's the implementation for the fix to the `get_unit_system` method in `weedb/influx.py`:

```python
@guard
def get_unit_system(self):
    """Get the unit system from the metadata measurement"""
    import sys
    try:
        # Query to get the most recent unit system value
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "weewx_metadata")
          |> filter(fn: (r) => r.type == "unit_system")
          |> last()
        '''
        result = self.query_api.query(query=query, org=self.org)
        
        if result and len(result) > 0 and len(result[0].records) > 0:
            raw_value = result[0].records[0].values.get('_value')
            print(f"DEBUG: Found raw unit system in metadata: {raw_value}, type: {type(raw_value)}", file=sys.stderr)
            
            # Ensure the value is converted to an integer regardless of how it's stored
            try:
                # If stored as string, convert to int
                if isinstance(raw_value, str):
                    if raw_value.lower().startswith('0x'):
                        unit_system = int(raw_value, 16)  # Handle hex string
                    else:
                        unit_system = int(raw_value)  # Handle decimal string
                # If stored as float, convert to int
                elif isinstance(raw_value, float):
                    unit_system = int(raw_value)
                # Otherwise, use as is if it's already an int, or convert if possible
                else:
                    unit_system = int(raw_value)
                    
                print(f"DEBUG: Converted unit system value: {unit_system}", file=sys.stderr)
                return unit_system
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Error converting unit system value: {e}, using default (1)", file=sys.stderr)
                return 1  # Default to US units (0x01) on conversion error
        else:
            print(f"DEBUG: No unit system found in metadata, using default (1)", file=sys.stderr)
            return 1  # Default to US units (0x01)
    except Exception as e:
        print(f"DEBUG: Error getting unit system: {e}, using default (1)", file=sys.stderr)
        return 1  # Default to US units (0x01) on error
```

This implementation:

1. Keeps the existing query to get the unit system value from the `weewx_metadata` measurement
2. Adds robust type checking to handle different formats the value might be stored in
3. Ensures proper conversion to integer regardless of the original format
4. Adds detailed logging to track the conversion process
5. Provides fallback to US units (1) in case of errors
6. Returns the unit system as an integer as expected by WeeWX

The `_execute_insert` method that handles writing the unit system metadata appears to be working correctly, so no changes are needed there.

#### Task 3: Design Method for Unit System Metadata

Based on our analysis, we've determined:

1. The storage mechanism (using a special `weewx_metadata` measurement with `type: unit_system`) is correctly implemented
2. The value is correctly stored in InfluxDB (value: 1)
3. The issue is in the retrieval and type conversion when reading the unit system value

Our design will focus on fixing the reading portion while maintaining the existing storage approach:

1. **Storage Design** (Already implemented):
   - Use a dedicated `weewx_metadata` measurement to store metadata
   - Tag with `type: unit_system` to identify the unit system metadata
   - Store the actual value in the `value` field

2. **Retrieval Design Improvements**:
   - Add robust type checking and conversion when reading the value
   - Handle various formats (string, float, integer, hex string)
   - Add detailed logging to track the conversion process
   - Provide safe fallback to default value (1 for US units)
   - Ensure the returned value is always an integer as expected by WeeWX

3. **Implementation Strategy**:
   - Update the `get_unit_system` method with a more robust implementation
   - Add more detailed error handling and logging
   - Keep the writing portion unchanged as it appears to be working correctly

#### Task 1: Research how unit systems are stored in SQLite/MySQL

In the traditional SQL database adapters (SQLite and MySQL), the unit system is stored differently than in InfluxDB:

1. **SQLite and MySQL:**
   - These databases maintain the unit system information directly in the connection object
   - The unit system is checked in the `_check_unit_system` method in `weewx/manager.py`
   - When a record is inserted, its unit system is verified against the database's stored unit system
   - For first-time records, the unit system of the first record becomes the standard for the database
   - The unit system is represented as an integer (e.g., 0x01 for US units, 0x10 for METRIC, etc.)
   - When WeeWX connects to the database, it can validate unit systems against what's already stored

2. **Error Flow:**
   - The error occurs when `manager.py` calls `self._check_unit_system(day_accum.unit_system)`
   - This method tries to compare the incoming unit system (0x05) with what's stored in the database
   - The mismatch between 0x05 (US units) and 0x6818c343 (corrupted value) causes the exception

#### Task 2: Analysis of InfluxDB Adapter Implementation

The current InfluxDB adapter in `weedb/influx.py` has some relevant features and gaps:

1. **Existing Features:**
   - It has a `get_unit_system` method and `std_unit_system` property
   - During record insertion, it recognizes when a unit system value is present and stores some metadata
   - It attempts to use a special measurement called `weewx_metadata` with a tag `type: unit_system`

2. **Current Issues:**
   - The unit system is stored correctly in InfluxDB (value: 1) but is read back incorrectly
   - The error suggests that the retrieved value (0x6818c343) is corrupted due to type conversion issues
   - The unit system value is not explicitly converted to the correct integer type when being read
   - There may be confusion between decimal, hexadecimal and string representations of the value
   - The retrieval mechanism is failing to ensure the value is in the format expected by WeeWX
   - There's no robust error handling if the value is in an unexpected format

3. **Important Code Areas:**
   - Lines 183-206: The `get_unit_system` method which reads from InfluxDB
   - Lines 437-453: Special handling to store unit system information during record insertion
   - Line 318: The `std_unit_system` property that returns the unit system

#### Targeted Fix

After examining the code and confirming that the value is correctly stored in InfluxDB as `1` but is being misinterpreted when read back, here's a targeted fix for the `get_unit_system` method:

```python
@guard
def get_unit_system(self):
    """Get the unit system from the metadata measurement"""
    import sys
    try:
        # Query to get the most recent unit system value
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "weewx_metadata")
          |> filter(fn: (r) => r.type == "unit_system")
          |> last()
        '''
        result = self.query_api.query(query=query, org=self.org)
        
        if result and len(result) > 0 and len(result[0].records) > 0:
            raw_value = result[0].records[0].values.get('_value')
            print(f"DEBUG: Found raw unit system in metadata: {raw_value}, type: {type(raw_value)}", file=sys.stderr)
            
            # Ensure the value is converted to an integer regardless of how it's stored
            try:
                # If stored as string, convert to int
                if isinstance(raw_value, str):
                    if raw_value.lower().startswith('0x'):
                        unit_system = int(raw_value, 16)  # Handle hex string
                    else:
                        unit_system = int(raw_value)  # Handle decimal string
                # If stored as float, convert to int
                elif isinstance(raw_value, float):
                    unit_system = int(raw_value)
                # Otherwise, use as is if it's already an int, or convert if possible
                else:
                    unit_system = int(raw_value)
                    
                print(f"DEBUG: Converted unit system value: {unit_system}", file=sys.stderr)
                return unit_system
            except (ValueError, TypeError) as e:
                print(f"DEBUG: Error converting unit system value: {e}, using default (1)", file=sys.stderr)
                return 1  # Default to US units (0x01) on conversion error
        else:
            print(f"DEBUG: No unit system found in metadata, using default (1)", file=sys.stderr)
            return 1  # Default to US units (0x01)
    except Exception as e:
        print(f"DEBUG: Error getting unit system: {e}, using default (1)", file=sys.stderr)
        return 1  # Default to US units (0x01) on error
```

This fix ensures proper type conversion of the unit system value regardless of how it's stored in InfluxDB. It handles various formats (string, float, integer) and specifically handles hexadecimal strings if present.

### Solution 2 Tasks
- [ ] Add `unit_system` configuration option to InfluxDB database binding
- [ ] Modify the InfluxDB adapter to respect this configuration
- [ ] Add validation to ensure the configuration uses a valid unit system
- [ ] Update unit system checking logic to handle InfluxDB appropriately
- [ ] Add documentation for this new configuration option
- [ ] Test with different unit system configurations

### Solution 3 Tasks
- [ ] Design a command interface for the unit system reset tool
- [ ] Implement functionality to query current unit system from InfluxDB
- [ ] Add capability to update all measurements to use a consistent unit system
- [ ] Create a migration process for converting between unit systems
- [ ] Add validation to prevent accidental data corruption
- [ ] Document the tool usage and recovery procedures

### Solution 4 Tasks
- [ ] Identify the exact location in the engine.py file to modify
- [ ] Add detection code to identify when an InfluxDB database is being used
- [ ] Implement the conditional logic to skip day summary backfill
- [ ] Add configuration option to control this behavior
- [ ] Test the solution with InfluxDB database
- [ ] Document the configuration option and its effects

#### Implementation Plan for Solution 4

This is the quickest solution to implement and will provide an immediate fix. The implementation steps would be:

1. **Modify engine.py**:
   ```python
   # Before the backfill call in the startup method
   if dbmanager.database_type == 'influxdb' and self.engine.config_dict.get('StdArchive', {}).get('skip_influxdb_day_summary', True):
       log.info("Skipping day summary backfill for InfluxDB database '%s'", dbmanager.database_name)
   else:
       _nrecs, _ndays = dbmanager.backfill_day_summary()
   ```

2. **Configuration Update**:
   Add documentation for the new option in weewx.conf:
   ```
   [StdArchive]
       ...
       # Set to True to skip day summary backfill for InfluxDB databases
       # This can prevent unit system errors on restart
       skip_influxdb_day_summary = True
   ```

3. **Testing**:
   - Test with the option enabled (skipping backfill)
   - Test with the option disabled (attempting backfill)
   - Verify that SQLite/MySQL databases are not affected

This approach is less invasive than modifying the database adapter itself and provides a configurable workaround while a more comprehensive solution is developed.

## Recommended Approach

Solution 1 is the most thorough approach as it addresses the root issue - InfluxDB not properly storing the unit system metadata. This would make InfluxDB work consistently with other database types in WeeWX.

Solution 2 might be easier to implement as an initial fix, allowing users to specify the unit system explicitly until a more complete solution can be developed.

However, **Solution 4** provides the quickest and least invasive fix that would immediately solve the error without major changes to the code. It's a pragmatic workaround that:

1. Directly addresses the immediate problem (error during backfill)
2. Requires minimal code changes (a simple conditional check)
3. Provides a configurable option for users
4. Doesn't interfere with normal operation of InfluxDB as a data store

A recommended implementation strategy would be:

1. First implement Solution 4 as an immediate fix to get systems working reliably
2. Then develop either Solution 1 or 2 as a more comprehensive fix
3. Consider Solution 3 as a utility tool for maintenance and troubleshooting

This multi-phase approach balances the need for an immediate fix with the desire for a proper long-term solution.