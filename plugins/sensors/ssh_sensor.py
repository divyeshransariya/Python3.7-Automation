from airflow.exceptions import AirflowException
from airflow.utils.decorators import apply_defaults

from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.sensors.base_sensor_operator import BaseSensorOperator

class SSHSensor(BaseSensorOperator):
    """
    Wait for some ssh command("UpTime") to succeed.
    """
    @ apply_defaults
    def __init__(self,
                ssh_conn_id,
                remote_host = None,
                poke_interval: float = 60,
                timeout: float = 60 * 15,
                mode: str = 'reschedule',
                *args, **kwargs):        
        
        super(SSHSensor, self).__init__(*args, **kwargs)
        self.ssh_conn_id = ssh_conn_id
        self.remote_host = remote_host
    
        if not self.ssh_conn_id:
            raise AirflowException("SSH Connection id is not provided")

    def poke(self, context):
        """
        Function that checks for ssh command("UpTime").
        """
        try:
            SSHOperator(task_id = context['task'].task_id, 
                        ssh_conn_id = self.ssh_conn_id, 
                        remote_host = self.remote_host, 
                        command = 'uptime').execute(context)
            return True

        except AirflowException:
            return False
    
"""
Usage:
task_start = SSHSensor(
    task_id = 'start_source',
    ssh_conn_id = 'connection ID',
    dag=dag)
"""