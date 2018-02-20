#!/usr/bin/python
import logging
import subprocess
from subprocess import call, check_output
from typing import List
from  urllib.error import HTTPError
import tempfile
import shutil
import tarfile
from os.path import isfile, join
import urllib.request
formatter = logging.Formatter('%(asctime)s  - %(levelname)s - %(message)s')
log_level = 'INFO' # default log level.
logger = None

LATEST_LIVECD_PATH_LINK = "http://distfiles.gentoo.org/releases/amd64/autobuilds/latest-stage3-amd64-nomultilib.txt"
LATEST_ISO_LINK = "http://distfiles.gentoo.org/releases/amd64/autobuilds/{}"
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

            # harcoded link to downloaded archive
            #stage3_archive = open("/tmp/tmpju_ys7nv", 'r')

            #stage3_dir = self.extract_stage_3(stage3_archive.name)
            stage3_dir = "/tmp/tmpqjbypp8j"

        finally:
            #commented for debug
            #stage3_archive.close()
            pass

class RunUtils:
    @staticmethod
    def execute_command(cmd: List[str], success_message=None):
        try:
            logger.debug('Execute cmd: %s',  ' '.join(cmd))
            out  = check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT)
            logger.debug(out)
            if success_message:
                logger.info(success_message)
        except subprocess.CalledProcessError as e:
            logger.error('Failed to execute %s: %s', ' '.join(cmd), e.output)

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
