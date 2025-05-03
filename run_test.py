#!/usr/bin/env python3
import subprocess
import time
import sys

def main():
    # Run weewxd with the test configuration
    p = subprocess.Popen(['python3', 'src/weewxd.py', 'weewx-influxdb-test.conf'], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
    
    print("Running WeeWX daemon with InfluxDB for 30 seconds...")
    
    # Let it run for 30 seconds
    time.sleep(30)
    
    # Terminate the process
    print("Terminating WeeWX process...")
    p.terminate()
    
    # Get the output
    stdout, stderr = p.communicate()
    
    # Write the output to files
    with open('weewx_stdout.log', 'w') as f:
        f.write(stdout.decode())
        
    with open('weewx_stderr.log', 'w') as f:
        f.write(stderr.decode())
    
    print("Output written to weewx_stdout.log and weewx_stderr.log")
    
    # Check for INSERT statements in the stderr output
    if 'DEBUG: Processing INSERT statement into InfluxDB' in stderr.decode():
        print("\nFOUND INSERT statements in the logs!")
    else:
        print("\nNo INSERT statements found in the logs.")
    
if __name__ == "__main__":
    main()