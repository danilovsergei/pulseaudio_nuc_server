#!/bin/bash
set -e
emerge -u gentoo-sources
mv /usr/src/main_config /usr/src/linux/.config

cd /usr/src/linux
cores=$(grep -c ^processor /proc/cpuinfo)
make -j$cores prepare
make -j$cores
make modules_install
make install

#Old modules rebuild. will work only in Gentoo Linux
emerge @module-rebuild