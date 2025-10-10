#!/bin/bash
# start.sh

# Wait a few seconds to ensure GUI session is ready
sleep 10

# Set environment variables for Wayland/XWayland
export DISPLAY=:0
export ELECTRON_ENABLE_WAYLAND=0

# Read 'code' value from JSON
code=$(jq -r '.code' ~/Atomte/secrets/details.json)

# Navigate to your project folder
cd ~/Atomte/Atomte_raspberrypi/atomte || exit

# Wait until the site is live (port 3000 responding)
echo "Waiting for React app to start..."
until curl -s http://localhost:3000 > /dev/null; do
  sleep 2
done

echo "React app is live. Launching Electron..."

# Launch Electron and pass the code
npm run electron -- "$code" --no-sandbox

