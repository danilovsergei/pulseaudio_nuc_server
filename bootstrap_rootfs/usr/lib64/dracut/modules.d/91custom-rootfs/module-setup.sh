#!/bin/bash
# -*- mode: shell-script; indent-tabs-mode: nil; sh-basic-offset: 4; -*-
# ex: ts=8 sw=4 sts=4 et filetype=sh

check() {
    return 0
}

depends() {
    echo dmsquash-live
}

install() {
    inst_hook pre-pivot 01 "$moddir/copy_customrootfs.sh"
    inst_hook pre-pivot 01 "$moddir/set_permissions.sh"

}
