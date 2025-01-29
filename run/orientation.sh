#!/bin/bash


SERVICE_NAME="display-rotation.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
SCRIPT_PATH="/usr/local/bin/set-display-rotation.sh"


if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please rerun with sudo."
    exit 1
fi


cat << 'EOF' > $SCRIPT_PATH
#!/bin/bash
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export WAYLAND_DISPLAY="wayland-0"

# Rotate the display using wlr-randr
/usr/bin/wlr-randr --output HDMI-A-1 --transform 270
EOF


chmod +x $SCRIPT_PATH
echo "Display rotation script created at $SCRIPT_PATH"


cat << EOF > $SERVICE_PATH
[Unit]
Description=Set display rotation for Wayland
After=graphical.target

[Service]
User=$(logname)
Environment="XDG_RUNTIME_DIR=/run/user/$(id -u)"
Environment="WAYLAND_DISPLAY=wayland-0"
ExecStart=$SCRIPT_PATH
Restart=on-failure

[Install]
WantedBy=graphical.target
EOF

echo "Systemd service created at $SERVICE_PATH"


systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME


systemctl status $SERVICE_NAME --no-pager

echo "Setup complete! The display rotation will now persist across reboots."