# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from airflow.utils.decorators import apply_defaults
import ftplib

from airflow.contrib.sensors.ftp_sensor import FTPSensor
from airflow.contrib.hooks.ftp_hook import FTPHook

class WinFTPSensor(FTPSensor):
    """
    Waits for a file or directory to be present on FTP.
    Check file size whether it present
    or Not....
    """
    
    @apply_defaults
    def __init__(self, *args, **kwargs):
        """
        Create a new FTP sensor

        :param path: Remote file or directory path
        :type path: str
        :param fail_on_transient_errors: Fail on all errors,
            including 4xx transient errors. Default True.
        :type fail_on_transient_errors: bool
        :param ftp_conn_id: The connection to run the sensor against
        :type ftp_conn_id: str
        """
        super(WinFTPSensor, self).__init__(*args, **kwargs)

    def _create_hook(self):
        """Return connection hook."""
        return FTPHook(ftp_conn_id=self.ftp_conn_id)

    def _get_error_code(self, e):
        """Extract error code from ftp exception"""
        try:
            matches = self.error_code_pattern.match(str(e))
            code = int(matches.group(0))
            return code
        except ValueError:
            return e
    
    def poke(self, context):
        with self._create_hook() as hook:
            """
            Check if given file present on FTP Server
            Using FTP size command
            Returns True if File present otherwise False
            """
            try:
                self.log.info('Poking for %s', self.path)
                size = hook.get_size(self.path)
                """
                Checking file present in FTP server ?
                if Not then wait for poke_interval and again check
                file present or not using FTP size command
                On Absence of File FTP Throws an error 550!
                for more details refer https://en.wikipedia.org/wiki/List_of_FTP_server_return_codes
                """
                return size > 0

            except ftplib.error_perm as e:
                self.log.info('FTP error encountered: %s', str(e))
                error_code = self._get_error_code(e)
                if ((error_code != 550) and
                        (self.fail_on_transient_errors or
                            (error_code not in self.transient_errors))):
                    raise e

                return False

            return True


"""
Usage :
check_task = WinFTPSensor(task_id='file_sensor',
                        path = '/FTPUSER/file.xyz',
                        ftp_conn_id = 'ftp_nse_fo', 
                        fail_on_transient_errors = False,
                        poke_interval = 5 * 60, 
                        timeout = 10 * 60,
                        mode ='reschedule',
                        dag = dag)
"""
            
            
            