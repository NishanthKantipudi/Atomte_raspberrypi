#!/bin/bash
sleep 2
export DISPLAY=:0

CODE=$(jq -r '.code' "$(pwd)/../secrets/details.json")

# Launch Chromium in kiosk mode with the URL containing the fetched code
/usr/bin/chromium-browser --kiosk "http://localhost:3000?code=$CODE" &

sleep 5
wmctrl -a Chromium