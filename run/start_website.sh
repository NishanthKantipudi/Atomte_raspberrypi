#!/bin/bash
sleep 2
export DISPLAY=:0

/usr/bin/chromium-browser --kiosk http://localhost:3000 &
sleep 5
wmctrl -a Chromium