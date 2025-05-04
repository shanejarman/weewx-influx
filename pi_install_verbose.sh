#!/bin/bash
# Run poetry install with verbose output to see more details about the failure

cd /home/realwx/weewx-influx
PYTHONVERBOSE=1 poetry install -v