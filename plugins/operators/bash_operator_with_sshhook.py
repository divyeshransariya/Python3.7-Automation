from airflow.exceptions import AirflowException
from airflow.utils.decorators import apply_defaults

from airflow.operators.bash_operator import BashOperator

from airflow.contrib.hooks.ssh_hook import SSHHook

class BashOperatorwithSSHHook(BashOperator):
    template_fields = ('command_list','env')
    @apply_defaults
    def __init__(
            self,
            command_list,
            ssh_conn_id,
            remote_host=None,
            username=None,
            port=None,
            key_file=None,
            *args, **kwargs):
        assert isinstance(command_list, list), "arg commad_list should be type list, but passed:{}".format(type(command_list))
        super(BashOperatorwithSSHHook, self).__init__(bash_command="",*args, **kwargs)
        self.username = username
        self.ssh_conn_id = ssh_conn_id
        self.remote_host = remote_host
        self.key_file = key_file
        self.port = port
        self.command_list=command_list

        if not self.ssh_conn_id:
            if not (self.remote_host and self.username and self.port and self.keyfile):
                raise AirflowException("In absence of ssh_conn_id following should be provided "\
                    "(host, username, port, identityfile)")
        
    def execute(self, context):
        """
        Execute the bash command in a temporary directory
        which will be cleaned afterwards
        """
        # we won't allow username and key_file to override by user
        ssh_hook = SSHHook(ssh_conn_id=self.ssh_conn_id, remote_host=self.remote_host, port=self.port)
        
        # Load connection info into running command
        # like username, port, keyfile as $1 $2 $3 for script
        if not ssh_hook.key_file:
            raise AirflowException("Key file missing in conn_id:{0}".format(self.ssh_conn_id))

        common_args = [ssh_hook.username + '@' + ssh_hook.remote_host, ssh_hook.port, ssh_hook.key_file]
        self.command_list = [self.command_list[0]] + common_args + self.command_list[1:]
        
        self.bash_command = " ".join(self.command_list)
        
        return super(BashOperatorwithSSHHook, self).execute(context)