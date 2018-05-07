#!/bin/sh
# -*- mode: shell-script; indent-tabs-mode: nil; sh-basic-offset: 4; -*-
# ex: ts=8 sw=4 sts=4 et filetype=sh

# user can easilly provide networkmanager files
# with wrong  permissions
# Force correct permissions.
# Otherwise it will not be possible to connect to nuc.
nm_dir=$NEWROOT/etc/NetworkManager
sys_con_dir=$nm_dir"/system-connections"
if [ -d $nm_dir ]; then
  chown -R root:root $nm_dir
fi

if [ -d $sys_con_dir ]; then
   find $sys_con_dir -type f -exec chmod 600 '{}' \;
fi

# Make sure dispatcher scripts owned by root
# to make sure they will be actually executed.
dispatcher_dir=$nm_dir"/dispatcher.d"
chown -R root:root $dispatcher_dir

# Make sure everything under /home/pulse owned by pulse user
# pulseaudio will not star otherwise.
# chroot needed since pulse exists only under NEWROOT
chroot_pulse_dir=/home/pulse
pulse_dir=$NEWROOT$chroot_pulse_dir
if [ -d $pulse_dir ]; then
            out=$(LANG=C chroot "$NEWROOT" chown -R pulse:pulse $chroot_pulse_dir 2>&1)
            ret=$?
            info $out
fi