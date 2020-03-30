from string import Template
from airflow.contrib.operators.ssh_operator import SSHOperator
# get_outfiles_today_directory
#
# make directory in outfiles named as date of that day for task execution

run_cmd=Template("mkdir -p $basePath/outfiles/$today_date;cd $basePath/outfiles/; ln -fns $today_date today")

def make_outfiles_path(ssh_conn_id, basePath, today_date, **kwargs):
    remote_host=kwargs.get('remote_host', None)
    
    return SSHOperator(ssh_conn_id=ssh_conn_id,
        remote_host=remote_host,
        task_id = 'outfiles',
        command =run_cmd.substitute(basePath=basePath, today_date=today_date))        
    
