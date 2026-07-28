#!/bin/bash

# Default configuration
DEFAULT_HOST="http://localhost:8080"
DEFAULT_WORKERS=4
DEFAULT_LOCUST_FILE="locustfile.py"
DEFAULT_WEB_PORT=8089

# Function to show help information
show_help() {
    echo
    echo "========================================"
    echo "    Locust Distributed Cluster Starter"
    echo "========================================"
    echo
    echo "Usage:"
    echo "  ./start_locust_cluster.sh [options]"
    echo
    echo "Options:"
    echo "  -H, --host HOST      Target host URL (default: $DEFAULT_HOST)"
    echo "  -w, --workers NUM    Number of worker processes (default: $DEFAULT_WORKERS)"
    echo "  -f, --file FILE      Locust script file (default: $DEFAULT_LOCUST_FILE)"
    echo "  -p, --port PORT      Web interface port (default: $DEFAULT_WEB_PORT)"
    echo "  -h, --help          Show this help message"
    echo
    echo "Examples:"
    echo "  ./start_locust_cluster.sh --host http://api.example.com --workers 4"
    echo "  ./start_locust_cluster.sh -H http://test.com -w 2 -f my_test.py"
    echo
    exit 0
}

# Initialize variables
TARGET_HOST="$DEFAULT_HOST"
WORKER_COUNT="$DEFAULT_WORKERS"
LOCUST_FILE="$DEFAULT_LOCUST_FILE"
WEB_PORT="$DEFAULT_WEB_PORT"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -H|--host)
            TARGET_HOST="$2"
            shift 2
            ;;
        -w|--workers)
            WORKER_COUNT="$2"
            shift 2
            ;;
        -f|--file)
            LOCUST_FILE="$2"
            shift 2
            ;;
        -p|--port)
            WEB_PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

echo "========================================"
echo "    Starting Locust Distributed Cluster"
echo "========================================"
echo "Target Host: $TARGET_HOST"
echo "Worker Count: $WORKER_COUNT"
echo "Locust File: $LOCUST_FILE"
echo "Web Port: $WEB_PORT"
echo "========================================"
echo

# Check if file exists
if [ ! -f "$LOCUST_FILE" ]; then
    echo "ERROR: Locust file '$LOCUST_FILE' not found!"
    read -p "Press Enter to continue..."
    exit 1
fi

echo "Step 1: Starting Master node..."
# Start master in background with nohup to keep it running
nohup locust -f "$LOCUST_FILE" --master --host="$TARGET_HOST" --web-port="$WEB_PORT" > locust_master.log 2>&1 &
MASTER_PID=$!
echo "Master started with PID: $MASTER_PID"
sleep 3

echo "Step 2: Starting $WORKER_COUNT worker processes..."
for ((i=1; i<=WORKER_COUNT; i++)); do
    echo "Starting Worker $i..."
    nohup locust -f "$LOCUST_FILE" --worker --master-host=localhost > "locust_worker_$i.log" 2>&1 &
    WORKER_PID=$!
    echo "Worker $i started with PID: $WORKER_PID"
    if [ $i -ne $WORKER_COUNT ]; then
        sleep 1
    fi
done

echo
echo "========================================"
echo "Cluster started successfully!"
echo "Web Interface: http://localhost:$WEB_PORT"
echo "Target Host: $TARGET_HOST"
echo "Worker Count: $WORKER_COUNT"
echo "========================================"
echo
echo "Log files:"
echo "  Master: locust_master.log"
echo "  Workers: locust_worker_*.log"
echo
echo "To stop the cluster, run: ./stop_locust_cluster.sh"
echo
read -p "Press Enter to continue..."