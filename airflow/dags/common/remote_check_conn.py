from airflow.models import DAG

from sensors.ssh_sensor import SSHSensor
from operators.bash_operator_with_sshhook import BashOperatorwithSSHHook

def remote_check_conn(parent_dag_name, child_dag_name, 
                        start_date,
                        schedule_interval,
                        default_args, 
                        remote_host=None,
                        *args, 
                        **kwargs):
    dag = DAG(
        '%s.%s' % (parent_dag_name, child_dag_name),
        schedule_interval=schedule_interval,
        default_args=default_args,
        start_date=start_date)
    
    reboot_remote = BashOperatorwithSSHHook(
        task_id ='remote_machine',
        remote_host=remote_host,
        command_list=['{{parmas.script_path}}/local/reboot_remote.sh '],
        dag=dag)

    wait_till_up = SSHSensor(
        task_id = 'wait_till_up',
        remote_host=remote_host,
        dag=dag)
    
    reboot_remote >> wait_till_up 

    return dag
