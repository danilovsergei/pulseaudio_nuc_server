#!/usr/bin/python
import os
import logging
import subprocess
from subprocess import call, check_output
from typing import List
from typing import Tuple
from  urllib.error import HTTPError
import tempfile
import shutil
import tarfile
from os.path import isfile, join
import urllib.request
import codecs
from subprocess import Popen, PIPE, STDOUT
import sys
from shutil import copyfile, copytree

formatter = logging.Formatter('%(asctime)s  - %(levelname)s - %(message)s')
log_level = 'INFO' # default log level.
logger = None

LATEST_LIVECD_PATH_LINK = "http://distfiles.gentoo.org/releases/amd64/autobuilds/latest-stage3-amd64-nomultilib.txt"
LATEST_ISO_LINK = "http://distfiles.gentoo.org/releases/amd64/autobuilds/{}"

MOUNT_BIN = "/bin/mount"
PORTAGE_DIR = "/usr/portage"

class LiveCdBootstrap:
    def __init__(self):
        pass

    def extract_stage_3(self, stage_archive):
        # TODO replace with tempfile.TemporaryDirectory once don't need to debug
        temp_dir = tempfile.mkdtemp()
        logger.debug('Extract stage3 into ' + temp_dir)
        with tarfile.open(stage_archive) as archive_file:
            archive_file.extractall(temp_dir)
        logger.info("Directory content extracted")
        return temp_dir

    def get_iso_link(self):
        iso_path = None
        try:
            response = urllib.request.urlopen(LATEST_LIVECD_PATH_LINK)
            data = response.read()
            text = data.decode('utf-8')
            for line in text.split('\n'):
                if 'tar.xz' in line:
                    iso_path = LATEST_ISO_LINK.format(line.split(' ')[0])
                    print(iso_path)
                    break
            if not iso_path:
                raise Exception('Latest gentoo iso not found on the server')
            return iso_path
        except HTTPError as e:
            logger.error(e.msg)

    def download_stage3(self, iso_link):
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            logger.debug('Save iso into ' + tmp_file.name)
            with urllib.request.urlopen(iso_link) as response, tmp_file:
                shutil.copyfileobj(response, tmp_file)
        return tmp_file

    def get_stage3(self):
        try:
            #iso_link = self.get_iso_link()
            #stage3_archive = self.download_stage3(iso_link)

            # harcoded link to emulate downloaded archive
            #stage3_archive = open("/tmp/tmpju_ys7nv", 'r')

            #stage3_dir = self.extract_stage_3(stage3_archive.name)

            #hardcoded link to emulate extracted stage3
            stage3_dir = "/tmp/tmp1a4bppnd"
            logger.info("Extracted stage3 into {}".format(stage3_dir))

            chroot = Chroot(stage3_dir)
            self.install_package(chroot)

        finally:
            #commented for debug
            # remove downloaded stage3 archive
            #stage3_archive.close()
            # remove  chroot directory. Should be done when new iso image created
            # shutil.rmtree(temp_dir)
            pass

    def install_package(self, chroot):
        chroot.copy_dir_content_to_chroot(
            RunUtils.get_rootfs_dir(),
            chroot.get_chroot_dir())

        #RunUtils.execute_command_in_chroot(chroot, ['emerge --unmerge sys-fs/eudev'])
        #RunUtils.execute_command_in_chroot(chroot, ['emerge --unmerge udev'])
        #RunUtils.execute_command_in_chroot(chroot, ['emerge --newuse world'])
        #RunUtils.execute_command_in_chroot(chroot, ['emerge pulseaudio'])

        RunUtils.execute_command_in_chroot(chroot, ['systemctl enable avahi-daemon'])
        RunUtils.execute_command_in_chroot(chroot, ['systemctl enable sshd'])

        RunUtils.execute_command_in_chroot(chroot, ['groupadd -f plugdev'])

        RunUtils.execute_command_in_chroot(chroot, ['id -u pulse & >/dev/null || useradd -m -d /home/pulse pulse'])
        RunUtils.execute_command_in_chroot(chroot, ['usermod -G audio pulse'])
        RunUtils.execute_command_in_chroot(chroot, ['usermod -G plugdev pulse'])

        RunUtils.execute_command_in_chroot(chroot, ['echo "root:12345678" | chpasswd'])
        RunUtils.execute_command_in_chroot(chroot, ['echo "pulse:12345678" | chpasswd'])


        RunUtils.execute_command_in_chroot(chroot, ['runuser -l pulse -c \'systemctl --user enable pulseaudio\''])




class Chroot:
    def __init__(self, chroot_dir):
        self.chroot_dir = chroot_dir

        self.mount_chroot_dirs(self.chroot_dir)

    def mount_chroot_dirs(self, chroot_dir):
        self.__mount_chroot_dir("/sys", join(chroot_dir,"sys"))
        self.__mount_chroot_dir("/proc", join(chroot_dir,"proc"))
        self.__mount_chroot_dir("/dev", join(chroot_dir,"dev"))

        self.__mount_chroot_dir(
            self.__get_portage_dir(),
            join(chroot_dir,"usr/portage"))

    # TODO: implement logic to allow user specify his portage dir
    # or either dynamically download it and bind
    def __get_portage_dir(self):
        return PORTAGE_DIR


    def __mount_chroot_dir(self, source, target):
        if not os.path.exists(target):
            os.makedirs(target)
        if not MountUtils.is_mounted(target):
            MountUtils.mount(source, target)

    def copy_file_to_chroot(self, souce_file, target_file=None):
        if not target_file:
            target_file = souce_file
        if not os.path.isabs(souce_file):
            souce_file = join(RunUtils.get_rootfs_dir(), souce_file)
        if not os.path.isabs(target_file):
            target_file = join(self.chroot_dir, target_file)
        copyfile(souce_file, target_file)

    def copy_dir_content_to_chroot(self, souce_dir, target_dir=None):
        if not souce_dir:
            raise Exception('source dir could not be empty')
        if not target_dir:
            raise Exception('target  dir could not be empty')

        souce_dir = souce_dir + '/.'

        RunUtils.execute_command(['cp', '-fr', souce_dir, target_dir])


    def get_chroot_dir(self):
        return self.chroot_dir


class MountUtils:
    @staticmethod
    def is_mounted(target):
        out = RunUtils.execute_command(["cat", "/etc/mtab"])
        if out[0]:
            raise Exception("Failed to check mount status for {}: {}".format(target, out[1]))
        for line in out[1].split('\n'):
            columns = line.split(" ")
            if len(columns) > 1 and codecs.decode(columns[1] , "unicode_escape") == target:
                return True
        return False

    @staticmethod
    def mount(source, target):
        cmd = [MOUNT_BIN, "-o", "bind", source, target ]
        RunUtils.execute_command(
            cmd,
            "Sucessfully mounted {} to {}".format(source, target))

class RunUtils:
    @staticmethod
    def execute_command(cmd: List[str], success_message=None) -> Tuple[int, str]:
        try:
            str_cmd = ' '.join(cmd)
            logger.debug("Execute cmd: {}".format(str_cmd))
            out  = check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT)
            logger.debug(out)
            if success_message:
                logger.info(success_message)
            return (0, out)
        except subprocess.CalledProcessError as e:
            logger.error('Failed to execute %s: %s', ' '.join(cmd), e.output)
            return (1, e.output)

    @staticmethod
    def execute_command_in_chroot(chroot, cmd: List[str]) -> str:
        str_cmd = ''.join(cmd)
        chroot_cmd = " ".join([
            "/usr/bin/chroot", chroot.get_chroot_dir(), "/bin/bash",
            "-c", "\"" +str_cmd + "\""
        ])
        out = []
        proc = Popen([chroot_cmd], shell=True, stdout=PIPE, stderr=STDOUT, universal_newlines=True)
        for line in iter(proc.stdout.readline, ''):
            out.append(line)
            logger.info('output: {}'.format(line))
        proc.terminate()
        proc.wait(timeout=0.2)
        logger.info("code = %s", proc.returncode)
        if proc.returncode != 0:
            raise Exception(
                "Failed to execute command in {} chroot: {} , {}"
                    .format(chroot.get_chroot_dir(), str_cmd, '\n'.join(out)))
        return '\n'.join(out)

    @staticmethod
    def get_root_dir():
        return os.path.dirname(
            os.path.dirname(os.path.realpath(sys.argv[0])))

    @staticmethod
    def get_rootfs_dir():
        return join(RunUtils.get_root_dir(), "rootfs")

class LogUtils:

    @staticmethod
    def getLogger(log_level):
        file_logger = logging.getLogger('file_logger')
        file_logger.setLevel(log_level)
        fh = logging.FileHandler('livecd_bootstrap.log')
        fh.setFormatter(formatter)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)

        file_logger.addHandler(fh)
        file_logger.addHandler(ch)
        return  file_logger

if __name__ == "__main__":
    logger = LogUtils.getLogger('DEBUG')
    bootstrap = LiveCdBootstrap()
    bootstrap.get_stage3()
