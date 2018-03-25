#!/bin/bash
set -e
emerge -u grub
emerge -u dracut
emerge -u sys-fs/lvm2

emerge -u net-misc/networkmanager

systemctl enable NetworkManager
systemctl enable sshd