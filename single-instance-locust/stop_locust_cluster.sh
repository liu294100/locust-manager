#!/bin/bash

echo "Stopping all Locust processes..."

# Kill all python processes running locust
pkill -f "locust.*master" 2>/dev/null
pkill -f "locust.*worker" 2>/dev/null

# Alternative method: kill all python processes with locust in command line
pgrep -f "python.*locust" | xargs -r kill -9 2>/dev/null

echo "All Locust processes have been stopped."
sleep 2