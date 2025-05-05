#!/bin/bash

# Start the geometry agents
echo "Starting geometry agents..."

# Start each agent on its own port
uvicorn agents.area_agent.__main__:app --port 8004 &
uvicorn agents.perimeter_agent.__main__:app --port 8005 &
uvicorn agents.geometry_host_agent.__main__:app --port 8006 &

echo "Starting Streamlit UI..."
streamlit run geometry_ui.py &

echo "All services started!"
echo "Access the Geometry Calculator at http://localhost:8501"
echo "Press Ctrl+C to stop all services"

# Wait for user to press Ctrl+C
wait