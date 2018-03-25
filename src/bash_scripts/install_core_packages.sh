#!/bin/bash
set -e
emerge -u app-portage/eix
chmod o+w /var/cache/eix
eix-update
eix -Ic sys-fs/eudev | grep -v [I] || emerge --unmerge sys-fs/eudev
eix -Ic virtual/udev | grep -v [I] || emerge --unmerge virtual/udev

# openssl update conflicts with currently installed version due
# to changed bindist flag
# after unmerge new version will be installed as dependency
eix -Ic dev-libs/openssl | grep -v [I] || emerge --unmerge dev-libs/openssl
emerge -u dev-libs/openssl

emerge --newuse world

echo "root:12345678" | chpasswd
