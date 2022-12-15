#!/usr/bin/python
import os
import logging
import subprocess
from subprocess import check_output
from typing import List
from typing import Tuple
from  urllib.error import HTTPError
import tempfile
import shutil
from os.path import join, exists, basename
import urllib.request
import codecs
from subprocess import Popen, PIPE, STDOUT
import sys
from shutil import copyfile
import argparse
import tarfile
from datetime import datetime

formatter = logging.Formatter('%(asctime)s  - %(levelname)s - %(message)s')
default_log_level = 'INFO' # default log level.
logger = None

REPO = "http://distfiles.gentoo.org/releases/amd64/autobuilds/"
LATEST_LIVECD_PATH_LINK = REPO + "latest-stage3-amd64-nomultilib.txt"

# binaries required on the host system
MOUNT_BIN = "mount"
UMOUNT_BIN = "umount"
MKSQUASHFS = "mksquashfs"
GRUB_MKRESCUE = "grub-mkrescue"
GRUB_MKIMAGE = "grub-mkimage"
GIT = "git"
CHROOT="chroot"

# include more modules than needed to be future proof
GRUB_MKIMAGE_MODULES = [
    "fat", "iso9660", "part_gpt", "part_msdos", "normal", "boot",
    "linux", "configfile", "loopback", "chain", "efifwsetup", "efi_gop",
    "efi_uga", "ls", "search", "search_label", "search_fs_uuid",
    "search_fs_file", "gfxterm", "gfxterm_background",
    "gfxterm_menu", "test", "all_video", "loadenv", "exfat",
    "ext2", "ntfs", "btrfs", "hfsplus", "udf", "probe"
]

class LiveCdBootstrap:
    def __init__(self):
        self.os_tmp_dir = args.temp_dir
        os.makedirs(RunUtils.get_kernel_dir(), exist_ok=True)
        os.makedirs(RunUtils.get_boot_dir(), exist_ok=True)

    def extract_stage_3(self, stage_archive):
        temp_dir = tempfile.mkdtemp(suffix="pulse_livecd", dir=self.os_tmp_dir)
        logger.info('Extract stage3 into ' + temp_dir)
        with tarfile.open(stage_archive) as archive_file:
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(archive_file, temp_dir)
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
                    iso_path = join(REPO, line.split(' ')[0])
                    break
            if not iso_path:
                raise Exception('Latest gentoo iso not found on the server')
            return iso_path
        except HTTPError as e:
            logger.error(e.msg)

    def download_stage3(self, iso_link):
        with tempfile.NamedTemporaryFile(delete=False, dir=self.os_tmp_dir) as tmp_file:
            logger.debug('Save iso into ' + tmp_file.name)
            with urllib.request.urlopen(iso_link) as response, tmp_file:
                shutil.copyfileobj(response, tmp_file)
        return tmp_file

    def __get_stage3_archive(self):
        if args.local_stage3_archive:
            stage3_archive = open(args.local_stage3_archive, 'r')
            logger.info("Use preconfigured stage3 archive {}"
                        .format(stage3_archive.name))
        else:
            iso_link = self.get_iso_link()
            logger.info("Download stage3 from %s", iso_link)
            stage3_archive = self.download_stage3(iso_link)
        return stage3_archive

    def generate_initramfs(self, chroot):
        chroot.copy_dir_content_to_chroot(
            join(RunUtils.get_rootfs_dir(), 'usr/lib64/dracut'),
            join(chroot.get_chroot_dir(), 'usr/lib64/dracut'))

        # install initrd image
        kver = chroot.get_kernel_version()
        if not kver:
            raise Exception("No kernel installed. Install kernel first")
        chroot.execute_command_in_chroot(
            'dracut --force --force-add "custom-rootfs" --kver={}'
                .format(kver))

    def __install_kernel(self, chroot):
        if args.skip_kernel_install:
            return
        chroot.copy_file_to_chroot(
            join(RunUtils.get_configs_dir(), "main_config"),
            "usr/src/main_config"
        )
        # compile and install kernel
        chroot.execute_script_in_chroot(
            join(RunUtils.get_scripts_dir(), "install_kernel.sh"))

    def install_fresh_stage3(self):
        stage3_archive = None
        try:
            stage3_archive = self.__get_stage3_archive()
            stage3_dir = self.extract_stage_3(stage3_archive.name)
            # check separately because broken symlink not identified by os.path.exists
            if os.path.islink(RunUtils.get_latest_chroot_symlink()):
              os.unlink(RunUtils.get_latest_chroot_symlink())              
            elif os.path.exists(RunUtils.get_latest_chroot_symlink()):
             os.remove(RunUtils.get_latest_chroot_symlink())

            os.symlink(stage3_dir, RunUtils.get_latest_chroot_symlink())
            logger.info(
                "Extracted and linked stage3 {} to {}".format(
                    stage3_dir, RunUtils.get_latest_chroot_dir()))
            return stage3_dir
        except:
            raise
        finally:
            if stage3_archive:
                stage3_archive.close()
                os.remove(stage3_archive.name)

    def create_livecd(self):
        stage3_dir = None
        chroot = None
        bootstrap_succeed = False
        try:
            if not args.chroot_dir:
                stage3_dir = self.install_fresh_stage3()
            else:
                stage3_dir = args.chroot_dir
                logger.info("Use preconfigured stage3 dir {}"
                        .format(stage3_dir))
            chroot = Chroot(stage3_dir)

            self.__bootstrap_rootfs(chroot)
            self.__install_kernel(chroot)
            self.__install_core_packages(chroot)
            self.__install_packages(chroot)
            self.generate_initramfs(chroot)
            self.generate_usb_image(chroot)
            bootstrap_succeed = True
        except:
            raise
        finally:
            # leave chroot dir in case if something went wrong
            self.__cleanup(
                chroot, stage3_dir,
                remove_chroot=bootstrap_succeed)

    def __cleanup(self, chroot, stage3_dir, remove_chroot=False):
        # cleanup stage3 dir only if user didnt provide its own dir
        if not args.chroot_dir and stage3_dir:
            if chroot:
                chroot.umount_chroot_dirs()
            if not args.skip_cleanup and remove_chroot:
                logger.info("Cleanup chroot dir %s", stage3_dir)
                shutil.rmtree(stage3_dir)

    def __bootstrap_rootfs(self, chroot):
        """Copies custom rootfs necessary to build iso
        to the chroot"""
        chroot.copy_dir_content_to_chroot(
            RunUtils.get_rootfs_dir(),
            chroot.get_chroot_dir())

    def __install_core_packages(self, chroot):
        if not chroot.is_file_exist_in_chroot("/bin/systemctl"):
            chroot.execute_script_in_chroot(
                join(RunUtils.get_scripts_dir(), "install_core_packages.sh"))

    def __install_packages(self, chroot):
        if not chroot.is_file_exist_in_chroot("/usr/bin/pulseaudio"):
            chroot.execute_script_in_chroot(
                join(RunUtils.get_scripts_dir(), "install_pulseaudio.sh"))

        chroot.execute_script_in_chroot(
            join(RunUtils.get_scripts_dir(), "install_sysutils.sh"))

    def __copy_kernel_files(self, chroot, final_image_dir):
        grub_dir = join(final_image_dir, 'boot/grub')
        os.makedirs(grub_dir)
        copyfile(
            join(RunUtils.get_configs_dir(), "inside_iso_grub.cfg"),
            join(grub_dir, "grub.cfg")
        )
        kver = chroot.get_kernel_version()
        if not kver:
            raise Exception("No kernel install. Install kernel first")
        vmlinuz_name = "boot/vmlinuz-" + kver
        copyfile(
            join(chroot.get_chroot_dir(), vmlinuz_name),
            join(final_image_dir, "boot/vmlinuz")
        )
        initrd_name = "boot/initramfs-" + kver + '.img'
        copyfile(
            join(chroot.get_chroot_dir(), initrd_name),
            join(final_image_dir, "boot/initrd")
        )

    def __make_squashfs_image(self, chroot):
        rootfs_dir = join(self.os_tmp_dir, "rootfs")
        rootfs_image = join(rootfs_dir, 'LiveOS', 'rootfs.img')

        final_image_dir =  join(self.os_tmp_dir, "iso_dir")
        final_image = join(final_image_dir, 'LiveOS', 'squashfs.img')

        logger.info(
            "Create squashfs file structure at {}".format(final_image_dir))
        self.__cleanup_dir(final_image_dir)
        self.__cleanup_dir(rootfs_dir)

        os.makedirs(os.path.dirname(final_image))
        os.makedirs(os.path.dirname(rootfs_image))

        self.__copy_kernel_files(chroot, final_image_dir)
        chroot.umount_chroot_dirs()

        RunUtils.execute_command(
            [MKSQUASHFS, chroot.get_chroot_dir(), rootfs_image],
            fail_on_error=True)

        RunUtils.execute_command(
            [MKSQUASHFS, rootfs_dir, final_image],
            fail_on_error=True)
        return final_image_dir

    def generate_iso_image(self, chroot):
        if args.skip_making_iso:
            logger.info("skip image generation due to --skip_making_iso")
            return
        if not exists(RunUtils.get_usbimage_dir()):
            os.mkdir(RunUtils.get_usbimage_dir())
        iso_image = join(RunUtils.get_usbimage_dir(), "pulseaudio.iso")
        logger.info("Create ISO image at {}".format(iso_image))

        squashfs_image_dir = self.__make_squashfs_image(chroot)

        code, output = RunUtils.execute_command(
            [GRUB_MKRESCUE, "-o", iso_image, squashfs_image_dir,
             "-volid", "PULSEAUDIO_LIVE"],
            fail_on_error=True, print_output=True)

        # check that iso was actually created
        # because grub-mkrescue does not print error code on error.
        if exists(iso_image):
            logger.info("ISO sucessfully generated")
        else:
            raise Exception("Failed to create iso image {}".format(output))

    def __make_usb_archive(self, usb_archive):
        logger.info("Create usbimage archive at {}".format(usb_archive))
        if exists(usb_archive):
            os.remove(usb_archive)
        with tarfile.open(usb_archive, "w:xz") as tar:
            tar.add(
                RunUtils.get_usbimage_dir(),
                arcname=os.path.sep
            )

    def generate_usb_image(self, chroot, generate_archive=True):
        if args.skip_generate_usb_image:
            logger.info("Skip creation of usb root file system")

        logger.info(
            "Create usb root filesystem at {}".format(
                RunUtils.get_usbimage_dir()))
        timestamp = datetime.now().strftime('%Y-%m-%dT%H_%M')
        usb_archive = join(
            self.os_tmp_dir,
            "pulseaudio_nucserver_{}.tar.xz".format(timestamp))

        #cleanup old image
        if exists(RunUtils.get_usbimage_dir()):
            shutil.rmtree(RunUtils.get_usbimage_dir())
        os.mkdir(RunUtils.get_usbimage_dir())

        self.generate_iso_image(chroot)
        CustomRootFs(
            RunUtils.get_pulseaudio_rootfs_dir()).generate_custom_root_fs()
        self.__generate_efi_boot()
        logger.info(
            "Successfully created usb root filesystem at {}".format(
                RunUtils.get_usbimage_dir()))
        if not generate_archive or args.skip_generate_usb_image_archive:
            logger.info("Skip usbimage archive generation")
            return
        self.__make_usb_archive(usb_archive)

    def __generate_efi_boot(self):
        efi_suffix = "EFI/BOOT"
        efi_dir = join(RunUtils.get_usbimage_dir(), efi_suffix)
        efi_app = join(efi_dir, "bootx64.efi")
        output_grub_cfg = join(efi_dir, "grub.cfg")

        if exists(efi_dir):
            shutil.rmtree(efi_dir)
        os.makedirs(efi_dir)

        cmd = [
            GRUB_MKIMAGE,
            "-o", efi_app,
            "-O", "x86_64-efi", # no reason to support 32 bits platforms
            "-p", "/" + efi_suffix # points to grub.cfg location on the usb
        ]
        cmd.extend(GRUB_MKIMAGE_MODULES)

        RunUtils.execute_command(cmd, fail_on_error=True)
        if not exists(efi_app):
            raise Exception(
                "Failed to create efi application at {}".format(efi_app))
        logger.info(
            "Successfully created efi application at {}".format(efi_app))

        copyfile(
            join(RunUtils.get_configs_dir(), "loadiso_grub.cfg"),
            output_grub_cfg)

    def __cleanup_dir(self, directory):
        if os.path.exists(directory):
            shutil.rmtree(directory)
            os.mkdir(directory)


class CustomRootFs:
    def __init__(self, rootfs_path):
        self.os_tmp_dir = args.temp_dir
        self.rootfs_path = rootfs_path

    def generate_custom_root_fs(self, out_dir=None):
        if args.skip_custom_rootfs:
            return
        if not out_dir:
            out_dir = RunUtils.get_usbimage_dir()

        archive_name = join(
            out_dir, '00-pulseaudio_custom_rootfs.tar.bz2')
        cmd = ["tar", "-cjvf", archive_name, "-C", self.rootfs_path, "."]
        RunUtils.execute_command(
            cmd,
            "sucessfully created custom rootfs {}"
                .format(archive_name), fail_on_error=True)


class Chroot:
    def __init__(self, chroot_dir, prepare_chroot=True):
        self.chroot_dir = chroot_dir
        if prepare_chroot:
            self.mount_core_chroot_dirs()
            self.copy_file_to_chroot("/etc/resolv.conf")

    def mount_core_chroot_dirs(self):
        self.mount_chroot_dir("/sys", join(self.chroot_dir,"sys"))
        self.mount_chroot_dir("/proc", join(self.chroot_dir,"proc"))
        self.mount_chroot_dir("/dev", join(self.chroot_dir,"dev"))

        self.mount_chroot_dir(
            RunUtils.get_portage_dir(),
            join(self.chroot_dir,"usr/portage"))

        self.mount_chroot_dir(
            RunUtils.get_boot_dir(),
            join(self.chroot_dir, "boot"))
        self.mount_chroot_dir(
            RunUtils.get_kernel_dir(),
            join(self.chroot_dir, "usr/src"))

    def umount_chroot_dirs(self):
        for mount in MountUtils.get_mounts():
            if mount[1].startswith(self.chroot_dir):
                MountUtils.umount_by_path(mount[1])

    def mount_chroot_dir(self, source, target):
        os.makedirs(target, exist_ok=True)
        if not MountUtils.is_mounted(target):
            MountUtils.mount(source, target)

    def execute_command_in_chroot(self, cmd: str) -> str:
        chroot_cmd = " ".join([
            CHROOT, self.chroot_dir, "/bin/bash",
            "-c", "\"" +cmd + "\""
        ])
        logger.debug("Execute cmd: %s", chroot_cmd)
        out = []
        proc = Popen([chroot_cmd],
                     shell=True,
                     stdout=PIPE,
                     stderr=STDOUT,
                     universal_newlines=True)
        for line in iter(proc.stdout.readline, ''):
            out.append(line)
            logger.info('output: {}'.format(line))
        proc.terminate()
        proc.wait(timeout=0.2)
        if proc.returncode != 0:
            raise Exception(
                "Failed to execute command in {} chroot: {} , {}"
                    .format(self.chroot_dir, cmd, '\n'.join(out)))
        return '\n'.join(out)

    def execute_script_in_chroot(self, local__file_path):
        remote_file_path =  join("/tmp", basename(local__file_path))
        self.copy_file_to_chroot(local__file_path, remote_file_path)
        self.execute_command_in_chroot("chmod +x " + remote_file_path)
        self.execute_command_in_chroot(remote_file_path)

    def copy_file_to_chroot(self, souce_file, target_file=None):
        if not target_file:
            target_file = souce_file
        if not os.path.isabs(souce_file):
            souce_file = join(RunUtils.get_rootfs_dir(), souce_file)
        if not os.path.isabs(target_file):
            target_file = join(self.chroot_dir, target_file)
        else:
            target_file = self.chroot_dir + target_file
        copyfile(souce_file, target_file)

    def copy_dir_content_to_chroot(self, souce_dir, target_dir=None):
        if not souce_dir:
            raise Exception('source dir could not be empty')
        if not target_dir:
            raise Exception('target  dir could not be empty')

        souce_dir = souce_dir + '/.'

        RunUtils.execute_command(
            ['cp', '-fr', souce_dir, target_dir],
            fail_on_error=True)

    def get_chroot_dir(self):
        return self.chroot_dir

    def get_kernel_version(self):
        return self.execute_command_in_chroot(
            "ls -1 /lib/modules").replace('\n', '')

    def is_file_exist_in_chroot(self, file_path):
        cmd = '[[ -f {} ]] && echo "True"|| exit 0'.format(file_path)
        if self.execute_command_in_chroot(cmd):
            return True
        else:
            return False


class MountUtils:
    @staticmethod
    def is_mounted(target):
        for mount in MountUtils.get_mounts():
            if mount[1] == target:
                return True
        return False

    @staticmethod
    def get_mounts():
        out = RunUtils.execute_command(
            ["cat", "/etc/mtab"],
            print_output=False)
        if out[0]:
            raise Exception("Failed to read /etc/mtab")
        mounts = []
        for line in out[1].split('\n'):
            columns = line.split(" ")
            if len(columns) > 1:
                mounts.append(
                    (columns[0],
                     codecs.decode(columns[1] , "unicode_escape")))
        return mounts

    @staticmethod
    def umount_by_path(path):
        exitcode, message = RunUtils.execute_command(
            [UMOUNT_BIN, "-l", path],
            success_message="Successfully umounted {}".format(
                path),
            fail_on_error=True)
        if exitcode !=0:
            raise Exception(message)

    @staticmethod
    def mount(source, target):
        cmd = [MOUNT_BIN, "-o", "bind", source, target ]
        code, result = RunUtils.execute_command(
            cmd,
            "Sucessfully mounted {} to {}".format(source, target),
            fail_on_error=True)
        if code != 0:
            raise Exception(result)


class RunUtils:
    @staticmethod
    def execute_command(
            cmd: List[str],
            success_message=None,
            print_output=True,
            fail_on_error=False) -> Tuple[int, str]:
        try:
            str_cmd = ' '.join(cmd)
            logger.debug("Execute cmd: {}".format(str_cmd))
            out = check_output(
                cmd,
                universal_newlines=True,
                stderr=subprocess.STDOUT)
            if print_output:
                logger.debug(out)
            if success_message:
                logger.info(success_message)
            return (0, out)
        except subprocess.CalledProcessError as e:
            logger.error('Failed to execute %s: %s', str_cmd, e.output)
            if fail_on_error:
                raise Exception('Failed to execute {}: {}'.format(str_cmd, e.output))
            return (1, e.output)

    @staticmethod
    def get_root_dir():
        return os.path.dirname(
            os.path.dirname(os.path.realpath(sys.argv[0])))

    @staticmethod
    def get_rootfs_dir():
        return join(RunUtils.get_root_dir(), "bootstrap_rootfs")

    @staticmethod
    def get_pulseaudio_rootfs_dir():
        return join(RunUtils.get_root_dir(), "pulseaudio_rootfs")

    @staticmethod
    def get_scripts_dir():
        return join(RunUtils.get_root_dir(), "src/bash_scripts")

    @staticmethod
    def get_configs_dir():
        return join(RunUtils.get_root_dir(), "src/configs")

    @staticmethod
    def get_kernel_dir():
        return join(args.temp_dir, "kernel_src")

    @staticmethod
    def get_boot_dir():
        return join(args.temp_dir, "boot")

    @staticmethod
    def get_usbimage_dir():
        return join(args.temp_dir, "usbimage")

    @staticmethod
    def get_portage_dir():
        if args.portage_dir:
            return args.portage_dir
        portage_dir=join(args.temp_dir, "portage")
        if not os.path.exists(portage_dir):
            os.makedirs(portage_dir)
            cmd = [
                GIT, "clone",
                 "https://github.com/gentoo/gentoo.git",
                 portage_dir]
            RunUtils.execute_command(cmd, fail_on_error=True)
        return portage_dir
    
    @staticmethod
    def which(program):
        def is_exe(fpath):
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        fpath, fname = os.path.split(program)
        if fpath:
            if is_exe(program):
                return program
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

        return None


    @staticmethod
    def get_latest_chroot_symlink():
        """Just return latest_chroot symlink without checking
        if it exists"""
        return join(args.temp_dir, "latest_chroot")

    @staticmethod
    def get_latest_chroot_dir():
        """Resolves latest_chroot symlink to real path
        Complains if it does not exist"""        
        symlink = RunUtils.get_latest_chroot_symlink()
        if not os.path.exists(symlink):
            raise Exception(
                "{} symlink must exist and "
                "point to the existing stage3 path".format(symlink))
        return os.path.realpath(symlink)
        

class LogUtils:

    @staticmethod
    def getLogger():
        if args.log_level:
            log_level = args.log_level
        else:
            log_level = default_log_level

        file_logger = logging.getLogger('file_logger')
        file_logger.setLevel(log_level)
        fh = logging.FileHandler('livecd_bootstrap.log', 'w')
        fh.setFormatter(formatter)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)

        file_logger.addHandler(fh)
        file_logger.addHandler(ch)
        return  file_logger


class Main:
    def parse_ags(self):
        parser = argparse.ArgumentParser(
            usage='use "%(prog)s --help" for more information',
            formatter_class=argparse.RawTextHelpFormatter,
            epilog=os.linesep.join([
                'Examples:',
                '--temp_dir=/Build/tmp',
                '  will use provided temp_dir to download latest stage3 there and make pulseaudio iso'
                '-temp_dir=/Build/tmp --chroot_dir=/Build/tmp/tmpkhjyu_fupulse_livecd',
                '  will use stage3 already extracted to chroot_dir to make pulseaudio iso'
                '-lo  cal_stage3_archive=stage3-amd64-nomultilib-20180301T214503Z.tar.xz',
                '  will use provided stage3 archive instead of dowloading latest one'
            ])
        )
        parser.add_argument("--local_stage3_archive",
                            help='\n'.join([
                                'Use provided stage3 instead of downloading.',
                                'latest one from gentoo.org'
                            ])
                            )

        parser.add_argument("--just_extract_stage3",
                            action="store_true",
                            help='\n'.join([
                                'Only extracts stage3 archive either provided',
                                'with --local_stage3_archive or downloads ',
                                'latest one from gentoo.org'
                            ])
                            )

        parser.add_argument("--chroot_dir",
                            help='\n'.join([
                                'Use provided chroot dir',
                                'instead of download and extract latest stage3'
                            ])
                            )

        parser.add_argument("--use_latest_chroot",
                            action="store_true",
                            default=False,
                            help=
                            '\n'.join([
                                'If specified will point chroot dir to temp_dir/latest_chroot '
                                'latest_chroot symlink created during extracting stage3',
                            ])
                            )

        parser.add_argument("--temp_dir",
                            required=True,
                            help='\n'.join([
                                'Use provided temp_dir to ',
                                'extract and compile livecd'
                            ])
                            )


        parser.add_argument("--skip_kernel_install",
                            action="store_true",
                            default=False,
                            help=
                            '\n'.join([
                                'If specified will skip to download and '
                                'compile latest gentoo-sources kernel.',
                            ])
                            )
        parser.add_argument("--portage_dir",
                            help='\n'.join([
                                'Will be mounted as portage to chroot'
                                'if specified. Otherwise fresh portage snapshot',
                                'will be cloned from gentoo git'
                            ])
                            )

        parser.add_argument("--skip_making_iso",
                            action="store_true",
                            default=False,
                            help=
                            '\n'.join([
                                'If specified will making iso image '
                            ])
                            )

        parser.add_argument("--skip_cleanup",
                            action="store_true",
                            default=False,
                            help=
                            '\n'.join([
                                'If specified will leave livecd chroot',
                                'after iso image created'
                            ])
                            )

        parser.add_argument("--generate_custom_rootfs",
                            required=False,
                            help='\n'.join([
                                'Generates custom rootfs archive will maybe',
                                'used over livecd image during boot',
                                'argument must be used on its own and could',
                                'not be combined with other options'
                            ])
                            )

        parser.add_argument("--skip_custom_rootfs",
                            action="store_true",
                            help='\n'.join([
                                'Will skip custom rootfs archive generation',
                                'if specified',
                            ])
                            )

        parser.add_argument("--generate_initramfs",
                            action="store_true",
                            help='\n'.join([
                                'Only generates initramfs',
                                'Assumes chroot environment already has',
                                'kernel and dracut installed',
                                'argument must be used on its own and could',
                                'not be combined with other options'
                            ])
                            )

        parser.add_argument("--generate_usb_image_dir",
                            action="store_true",
                            help='\n'.join([
                                'Generates full usb root directory',
                                'which is ready to copy to usb flash',
                                'Add --generate_usb_image_archive to also',
                                'create archive'
                            ])
                            )

        parser.add_argument("--generate_usb_image_archive",
                            action="store_true",
                            help='\n'.join([
                                'Generates archive with full usb root directory',
                                'which is ready to extract on usb flash'
                            ])
                            )

        parser.add_argument("--skip_generate_usb_image",
                            action="store_true",
                            help='\n'.join([
                                'Usb root file structure generation will be skipped',
                                'if specified',
                            ])
                            )

        parser.add_argument("--skip_generate_usb_image_archive",
                            action="store_true",
                            help='\n'.join([
                                'Usb root file structure will be generated ',
                                'at build directory.',
                                'However final archive generation will be skipped',
                            ])
                            )

        parser.add_argument("--generate_iso",
                            action="store_true",
                            help='\n'.join([
                                'Just generates new iso image if specified',
                            ])
                            )

        parser.add_argument("--umount_chroot",
                            action="store_true",
                            help='\n'.join([
                                'Unmounts all chroot directory external mounts',
                                'Requires --chroot_dir parameter',
                            ])
                            )

        parser.add_argument("--mount_chroot",
                            action="store_true",
                            help='\n'.join([
                                'Mounts all required external mounts to chroot',
                                'Requires --chroot_dir parameter',
                            ])
                            )

        parser.add_argument("--log_level",
                            help='\n'.join([
                                'Log level either INFO, WARNING, DEBUG',
                            ])
                            )
        return parser.parse_args()

    def check_binaries_exist(self):
        self.__file_exists(MOUNT_BIN)
        self.__file_exists(UMOUNT_BIN)
        self.__file_exists(MKSQUASHFS)
        self.__file_exists(GRUB_MKRESCUE)
        self.__file_exists(GRUB_MKIMAGE)
        self.__file_exists(GIT)

    def __file_exists(self, file):
        full_command = RunUtils.which(file)
        if not full_command or not os.path.exists(full_command):
            raise Exception(
                "'{}' command does not exist on the host system"
                    .format(file))

    def execute(self):
        self.check_binaries_exist()

        if args.use_latest_chroot:
            if args.chroot_dir:
                logger.warning(
                    "specified --chroot_dir will be ignored because"
                    "--use_latest_chroot has priority over it"
                )
            args.chroot_dir = RunUtils.get_latest_chroot_dir()
            logger.info("use {} dir".format(args.chroot_dir))

        if args.umount_chroot:
            if not args.chroot_dir:
                raise Exception("Please specify chroot dir")
            chroot = Chroot(args.chroot_dir, prepare_chroot=False)
            chroot.umount_chroot_dirs()
            return
        if args.mount_chroot:
            if not args.chroot_dir:
                raise Exception("Please specify chroot dir")
            Chroot(args.chroot_dir).mount_core_chroot_dirs()
            return

        if args.generate_custom_rootfs:
            CustomRootFs(args.generate_custom_rootfs) \
                .generate_custom_root_fs()
            return

        if not args.temp_dir:
            raise Exception("Please specify --temp_dir")

        if args.just_extract_stage3:
            LiveCdBootstrap().install_fresh_stage3()
            return

        def get_chroot():
          if not args.chroot_dir:
            raise Exception(
              "--chroot_dir must be provided "
              "or either --use_latest_chroot used")
          return Chroot(args.chroot_dir)

        # add targets using chroot below this point
        bootstrap = LiveCdBootstrap()
        # TODO check dir exists : /usr/lib/grub/x86_64-efi
        if args.generate_initramfs:
            bootstrap.generate_initramfs(get_chroot())
            return

        if args.generate_iso:
            bootstrap.generate_iso_image(get_chroot())
            return

        if args.generate_usb_image_dir \
                and not args.generate_usb_image_archive:
            bootstrap.generate_usb_image(
                get_chroot(), generate_archive=False)
            return

        if args.generate_usb_image_archive:
            bootstrap.generate_usb_image(
                get_chroot(), generate_archive=True)
            return

        bootstrap.create_livecd()

if __name__ == "__main__":
    main = Main()
    args = main.parse_ags()

    logger = LogUtils.getLogger()
    main.execute()
