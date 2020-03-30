from string import Template
from airflow.contrib.operators.ssh_operator import SSHOperator

# get_infiles_today_directory
#
# make directory in infiles named as date of that day for task execution

run_cmd=Template("mkdir -p $basePath/infiles/$today_date;cd $basePath/infiles/; ln -fns $today_date today")
def make_infiles_path(ssh_conn_id, basePath, today_date, **kwargs):
    remote_host=kwargs.get('remote_host',None)

    return SSHOperator(ssh_conn_id=ssh_conn_id,
        remote_host=remote_host,
        task_id = 'infiles',
        command =run_cmd.substitute(basePath=basePath, today_date=today_date))
    
