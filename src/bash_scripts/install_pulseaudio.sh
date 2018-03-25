#!/bin/bash
set -e

id -u pulse > /dev/null 2>&1 || useradd -m -d /home/pulse pulse
echo "pulse:12345678" | chpasswd

chown -R pulse:pulse /home/pulse
emerge -u pulseaudio

systemctl enable avahi-daemon

groupadd -f plugdev
usermod -G plugdev,audio pulse

runuser -l pulse -c 'systemctl --user enable pulseaudio'