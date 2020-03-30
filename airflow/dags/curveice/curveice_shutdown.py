import os
import pendulum
from datetime import datetime, timedelta
from string import Template

from airflow import DAG
from airflow.models import Variable

from common.remote_check_conn import remote_check_conn

from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator
from airflow.operators.subdag_operator import SubDagOperator

from airflow.contrib.hooks.ssh_hook import SSHHook

"""
    All Connection Info !!
    Everything related to web config goes here....
    remote_host is like < user_name > @ < machine_ip >
"""
SSH_CONN_ID = 'test_server'
SLACK_CONN_ID = 'slack'
remote_hook = SSHHook(ssh_conn_id = SSH_CONN_ID)
remote_host = remote_hook.username + '@' + remote_hook.remote_host

""" 
$HOME Environ. variable --> For AWS Machine (For e.g. Airflow Machine $HOME = /home/ec2-user)
$REMOTE_HOME Environ. variable --> For Remote Machine (For e.g. Axxela Machine $REMOTE_HOME = /home/silver)
"""
try :
    HOME = os.environ['HOME']
    REMOTE_HOME = 'home/silver'
    # REMOTE_HOME = check_output(["ssh", remote_host, "sh -c 'echo $HOME'"]).decode('ASCII').strip('\n')
except ValueError:
    print('$HOME Environ. variable or $REMOTE_HOME environ. variable does not exist ;(')


"""
    All store paths and script path information 
    available here you can add as well modify according to you NEEDS
"""
local_script_dir = Template('$HOME/task_chain/scripts').substitute(HOME = HOME) 
remote_store_path = Template('$HOME/tmp').substitute(HOME = REMOTE_HOME) # All .sh scripts are move to here (on remote machine)
script_path = Template('$HOME/airflow/bashScripts/').substitute(HOME = HOME) # All .sh scripts located here

if __name__ == "__main__":

    default_args = {
        'owner': 'Airflow',
        'depends_on_past': False,
        'email': ['divyesh.ransariya@silverleafcaps.com'],
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 0,
        'retry_delay': timedelta(seconds = 3),
    #    'on_failure_callback': task_fail_slack_alert,
    }

    '''
        Run this Dag daily at 4:00 PM, Daily
        runs on 2020-02-7   16:00:00
        next on 2020-02-8   16:00:00
    '''

    dag = DAG(
        'curveice_shutdown', default_args = default_args, start_date = datetime(2020, 2, 13), schedule_interval = '0 5 * * *')
    
    # print('ALL WELL SET'.center(50,' - '))

    latest_only = LatestOnlyOperator(task_id='latest_only', dag=dag)
    
    # command for copy to remote host
    copy_script_run_cmd = Template(script_path + 'copy_taskchain_scripts.sh $local_script_dir $remote_host $remote_store_path')
    copy_script_remote = BashOperator(
        task_id = 'copy_script_remote',
        bash_command = copy_script_run_cmd.substitute(local_script_dir=local_script_dir, remote_host=remote_host, remote_store_path=remote_store_path),
        dag = dag)


    reboot_remote = SubDagOperator(
        subdag=remote_check_conn('curveice_shutdown', 'reboot_remote', dag.start_date, dag.schedule_interval, default_args=default_args),
        task_id='reboot_remote',
        dag=dag)

    # reboot_remote = BashOperator(task_id='reboot_remote',bash_command='sleep 3',dag=dag)

    zip_move_cmd=Template(script_path + 'zip_move_logs.sh $remote_host $remote_store_path $drop_location $run_date')
    zip_move_logs = BashOperator(
        task_id = 'zip_move_logs',
        bash_command = zip_move_cmd.substitute(remote_host = remote_host, remote_store_path = remote_store_path,
            drop_location = 'axxela-bas1', run_date='{{ next_ds }}'),
        dag = dag)

    copy_persist_files_notice_cmd = Template(script_path + 'copy_persist_files_notice.sh $remote_host $remote_store_path')
    copy_persist_files_notice = BashOperator(
        task_id = 'copy_persist_files_notice',
        bash_command = copy_persist_files_notice_cmd.substitute(remote_host = remote_host, remote_store_path = remote_store_path),
        dag = dag)

    infiles_to_cloud_cmd = script_path + 'file-service-infiles.sh '
    infiles_to_cloud = BashOperator(
        task_id = 'infiles_to_cloud',
        bash_command = infiles_to_cloud_cmd,
        dag = dag)


    outfiles_to_cloud_cmd = script_path + 'file-service-logs.sh '
    outfiles_to_cloud = BashOperator(
        task_id = 'outfiles_to_cloud',
        bash_command = outfiles_to_cloud_cmd,
        dag = dag)


    latest_only >> copy_script_remote >> reboot_remote

    reboot_remote >> [copy_persist_files_notice, zip_move_logs]

    zip_move_logs >> infiles_to_cloud

    infiles_to_cloud >> outfiles_to_cloud
    