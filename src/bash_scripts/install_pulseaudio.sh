#!/bin/bash
set -e

id -u pulse > /dev/null 2>&1 || useradd -m -d /home/pulse pulse
echo "pulse:12345678" | chpasswd

# allow pulse user to talk to systemd to restart pulseaudio service
auth_file=/etc/pam.d/system-auth
allow_systemd="-session        optional        pam_systemd.so"
grep -q "$allow_systemd" $auth_file || echo "$allow_systemd" >>  $auth_file

chown -R pulse:pulse /home/pulse
emerge -u pulseaudio

systemctl enable avahi-daemon

groupadd -f plugdev
usermod -G plugdev,audio pulse

runuser -l pulse -c 'systemctl --user enable pulseaudio'