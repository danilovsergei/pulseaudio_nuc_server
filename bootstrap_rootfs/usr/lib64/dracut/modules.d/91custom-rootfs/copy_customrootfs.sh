#!/bin/sh
# -*- mode: shell-script; indent-tabs-mode: nil; sh-basic-offset: 4; -*-
# ex: ts=8 sw=4 sts=4 et filetype=sh

function extract_custom {
  archives_dir=$1
  cd $archives_dir
  for archive in *-pulseaudio_custom_rootfs.tar.bz2; do
    tar -xvf $archive -C $NEWROOT
  done
}

# iso_dir exists when dracut boot args root=live:CDLABEL=PULSEAUDIO_LIVE
# used to load iso image without installing it on flash/disc
# it points to the directory where physical iso file present
iso_dir=/run/initramfs/isoscan

# livecd_dir points to the location where iso disc contents mounted
# consider it as root folder on flash when iso installed on flash.
livecd_dir=/run/initramfs/live

if [ -d $iso_dir ]; then
  extract_custom $iso_dir
else
  extract_custom $livecd_dir
fi



