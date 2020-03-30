from airflow.contrib.operators.ssh_operator import SSHOperator
from common.run_strat_task import get_task_run_cmd

# getStratTaskOperator 
# 
# returns a SSHOperator which run command(task) on remote server based on provided ssh_hook,taskName etc
def get_strat_task_operator(ssh_conn_id, taskName, taskMap, exportsMap, baseCodePath, baseStorePath,date,**kwargs):
    return SSHOperator(ssh_conn_id = ssh_conn_id,
        task_id = taskName,
        command = get_task_run_cmd(taskName, taskMap, exportsMap, baseCodePath, baseStorePath,date,**kwargs))

