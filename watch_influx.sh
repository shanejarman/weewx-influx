#!/bin/bash

# Script to watch the InfluxDB data stream

# Configuration from weewx-influxdb-test.conf
ORG="weewx"
TOKEN="aXwGB3kJzQgfRD9f1ibYcsmGbmj-9DExYoK_rbbqf2yS5DgbRTNR-kHC8SPOzr9Blfs5rrAMIOsvFMvOl0dA_A=="
BUCKET="weather_data"
HOST="http://localhost:8086"

# Optional parameters
INTERVAL=${1:-2}  # Default refresh interval: 2 seconds
RANGE=${2:-10s}   # Default time range: last 10 seconds

# Alternative loop since watch command is not available
while true; do
  clear
  echo "InfluxDB Data Stream (refreshing every ${INTERVAL}s, showing last ${RANGE})"
  echo "-----------------------------------------------------------------"
  influx query --org $ORG --token $TOKEN --host $HOST "from(bucket: \"$BUCKET\") |> range(start: -$RANGE)"
  echo "-----------------------------------------------------------------"
  echo "Press Ctrl+C to exit"
  sleep $INTERVAL
done