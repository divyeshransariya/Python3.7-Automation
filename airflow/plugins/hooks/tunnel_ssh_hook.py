# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os

from airflow.exceptions import AirflowException
from airflow.contrib.hooks.ssh_hook import SSHHook

class TunnelSSHHook(SSHHook):
    """
    Tunnel-Hook for ssh remote execution using Paramiko.
    ref: https://github.com/paramiko/paramiko
    This hook also lets you create ssh tunnel and serve as basis for SFTP file transfer

    :param hop_conn_id: connection id of Middle server (middle hop a.k.a public server)
        Thought the priority is given to the param passed during init
    :type hop_conn_id: str
    :param remote_conn_id: connection id to connect to private server via Tunnel
    :type remote_conn_id: str
    param hop_ssh_hook: predefined ssh_hook to use for remote execution.
        Either `hop_ssh_hook` or `hop_ssh_conn_id` needs to be provided.
    :type ssh_hook: airflow.contrib.hooks.ssh_hook.SSHHook
    """

    def __init__(self,
                remote_conn_id,
                hop_conn_id,
                hop_ssh_hook = None
                ):
    
        self.hop_ssh_hook = hop_ssh_hook

        # Use connection to override defaults
        if hop_conn_id:
            if self.hop_ssh_hook and isinstance(self.hop_ssh_hook, SSHHook):
                self.log.info("hop_conn_id is ignored when ssh_hop_hook is provided.")
            else:
                self.hop_ssh_hook = SSHHook(ssh_conn_id=hop_conn_id)

        if not self.hop_ssh_hook:
            raise AirflowException("Cannot operate without hop_ssh_hook or hop_conn_id.")

        if not remote_conn_id:
            raise AirflowException("Remote connection MUST BE provided")

        conn = self.get_connection(remote_conn_id)
        self.remote_port = conn.port
        self.remote_host_direct = conn.host

        # Set Parameter According TO remote_conn_id
        super(TunnelSSHHook, self).__init__(ssh_conn_id = remote_conn_id, remote_host = 'localhost')

    def get_conn(self):
        """
        Opens a ssh connection to the remote host.
        :rtype: paramiko.client.SSHClient
        Create Tunnel and connect using locahost to private server 
        Change port to local Binded port --> For connect to private server
        """ 
        try:
            tunnel = self.hop_ssh_hook.get_tunnel(self.remote_port, self.remote_host_direct)
            tunnel.start()

            assert self.remote_host == 'localhost', 'In local port fowarding localhost MUST BE needed!'
            self.port = tunnel.local_bind_port

        except Exception as e:
            raise AirflowException("SSH Tunnel error: %s"%(str(e)))

        # Connect to Private Server
        return super(TunnelSSHHook, self).get_conn()
