#!/bin/bash
# start_atomte.sh

# Wait a few seconds to ensure GUI session is ready
sleep 10

# Set environment variables for Wayland/XWayland
export DISPLAY=:0
export ELECTRON_ENABLE_WAYLAND=0

# Read 'code' value from JSON
code=$(jq -r '.code' Atomte/secrets/details.json)

# Navigate to your project folder
cd Atomte/Atomte_raspberrypi/Atomte_raspberrypi/atomte

# Launch Electron in fullscreen and pass the code
npm run electron -- "$code" --no-sandbox
