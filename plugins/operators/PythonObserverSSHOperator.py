from airflow.exceptions import AirflowException
from airflow.utils.decorators import apply_defaults

from airflow.operators.python_operator import PythonOperator
from airflow.contrib.operators.ssh_operator import SSHOperator

class PythonObserverSSHOperator(PythonOperator):
    @apply_defaults
    def __init__(
            self,
            ssh_conn_id,
            command,
            remote_host=None,
            *args, **kwargs):
        super(PythonObserverSSHOperator, self).__init__(*args, **kwargs)
        self.ssh_conn_id = ssh_conn_id
        self.remote_host = remote_host
        self.command=command
        
    def execute(self,context):
        assert('ssh_cmd_output' not in self.op_kwargs),'someone has already given value to ssh_cmd_output,please fix it'
        self.op_kwargs['ssh_cmd_output']=SSHOperator(
            task_id='ssh_cmd_output',
            ssh_conn_id=self.ssh_conn_id,
            remote_host=self.remote_host,
            do_xcom_push=True,
            command=self.command).execute(context).decode('utf-8')
        
        return super(PythonObserverSSHOperator, self).execute(context)