#!/bin/sh
# -*- mode: shell-script; indent-tabs-mode: nil; sh-basic-offset: 4; -*-
# ex: ts=8 sw=4 sts=4 et filetype=sh

iso_dir=/run/initramfs/isoscan
cd $iso_dir
for archive in *-pulseaudio_custom_rootfs.tar.bz2; do
  tar -xvf $archive -C $NEWROOT
done


