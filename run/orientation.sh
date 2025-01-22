#!/bin/bash

# Define the rotation command
ROTATE_COMMAND="xrandr --output HDMI-1 --rotate left"

# Create the LightDM display-setup-script.sh if it doesn't exist
LIGHTDM_SCRIPT="/etc/lightdm/display-setup-script.sh"

if [ ! -f "$LIGHTDM_SCRIPT" ]; then
    echo "$ROTATE_COMMAND" | sudo tee $LIGHTDM_SCRIPT > /dev/null
    # Make the script executable
    sudo chmod +x $LIGHTDM_SCRIPT
    echo "Display setup script created at $LIGHTDM_SCRIPT"
else
    echo "Display setup script already exists, skipping creation."
fi

# Configure LightDM to use the setup script
LIGHTDM_CONF="/etc/lightdm/lightdm.conf"

if ! grep -q "display-setup-script=$LIGHTDM_SCRIPT" "$LIGHTDM_CONF"; then
    echo -e "\n[Seat:*]\ndisplay-setup-script=$LIGHTDM_SCRIPT" | sudo tee -a $LIGHTDM_CONF > /dev/null
    echo "LightDM configuration updated to use display-setup-script."
else
    echo "LightDM is already configured to use the display-setup-script."
fi

# Restart LightDM to apply changes
sudo systemctl restart lightdm
