from airflow.configuration import conf
from string import Template
import pendulum,logging
from datetime import datetime, timedelta

from airflow import DAG

from common.remote_check_conn import remote_check_conn
from curveice.run_strat_task_ice import taskMap
from curveice.basildon_server_config import server_tasks
from common.task_subdag import task_subdag
from common.make_outfiles_path import make_outfiles_path
from common.make_infiles_path import make_infiles_path

from airflow.operators.latest_only_operator import LatestOnlyOperator
from operators.slack_operator import task_fail_slack_alert
from airflow.operators.subdag_operator import SubDagOperator
from airflow.operators.dummy_operator import DummyOperator
from operators.PythonObserverSSHOperator import PythonObserverSSHOperator
from operators.bash_operator_with_sshhook import BashOperatorwithSSHHook
from common.helper_functions import *

""" 
    All Dags are parse from this location
    and all files which is used by this module
    their paths are relative to DAG_PATH 
"""
try:
    # In Our case --> /home/divyesh/git/etcetera/release_server/airflow/dags
    DAG_PATH = conf.get('core','dags_folder')
except Exception as e:
    logging.exception(e)

default_args = {
    'owner': 'Airflow',
    'depends_on_past': False,
    'email': ['divyesh.rajkotiya@silverleafcaps.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'email_on_sla' : False,
    'retries': 0,
    'retry_delay': timedelta(seconds=1),
    'on_failure_callback': task_fail_slack_alert,
    'ssh_conn_id': 'ssh_divyesh',
    'params': {
        'script_path'       : Template('$DAG_PATH/../scripts').substitute(DAG_PATH=DAG_PATH),
        'slack_alerts'      : 'C0HFV1WP5', # Slack ID for #ops-market
        'remote_store_path' : Template('$HOME/deploy').substitute(HOME = '/home/silver'),
        'baseCodePath'      : Template('$HOME/deploy').substitute(HOME = '/home/silver'),
        'baseStorePath'     : Template('$HOME/deploy').substitute(HOME = '/home/silver'),
        'telemetry_path'    : '/home/divyesh/git/blackbird/blackbird/infra/telemetry_messages.d',
        'task_operator_info' : {'file' : 'run_strat_task_ice', 'package' : 'curveice',
                                'function' : 'get_strat_task_ice_operator'}
    }
}

ssh_conn_ice_root='ssh_divyesh'
for srv in server_tasks:
    with DAG('curveice_startup', default_args = default_args,
                schedule_interval = '30 10 * * *', start_date = datetime(2020, 3, 15,tzinfo=pendulum.timezone('Asia/Calcutta')),
                catchup = False) as dag:

        today_date = '{{tomorrow_ds}}'

        latest_only = LatestOnlyOperator(task_id='latest_only')

        copy_script_remote =BashOperatorwithSSHHook(
            task_id= 'copy_script_remote',
            command_list = ['{{params.script_path}}/local/copy_taskchain_scripts.sh ','{{params.script_path}}',
                    '{{params.remote_store_path}}'])

        if server_tasks[srv].has_root_access and server_tasks[srv].can_reboot:
            reboot_remote = SubDagOperator(
                subdag=remote_check_conn('curveice_startup', 'reboot_remote', dag.start_date, dag.schedule_interval,
                default_args=default_args,ssh_conn_id=ssh_conn_ice_root),
                task_id='reboot_remote')
        else:
            reboot_remote=DummyOperator(task_id='reboot_dummy')
        
        if server_tasks[srv].has_root_access:
            sync_time = BashOperatorwithSSHHook(
                    task_id = 'sync_time',
                    command_list = ['{{params.script_path}}/local/sync_time.sh '])
        else:
            sync_time=DummyOperator(task_id='sync_dummy')

        ## check disk space
        check_disk_space=PythonObserverSSHOperator(
            task_id='check_disk_space',
            command="df -BG {{params.bashCodePath}}/outfiles/ | tail -1 | awk '{print $4}'",
            python_callable=check_remote_disk_space,
            provide_context=True,
            op_kwargs={'space' : server_tasks[srv].desired_free_space})

        latest_only >> copy_script_remote >> reboot_remote >> sync_time >>check_disk_space

        infiles_path = make_infiles_path(default_args['ssh_conn_id'],'{{params.baseCodePath}}',today_date)

        outfiles_path = make_outfiles_path(default_args['ssh_conn_id'],'{{params.baseCodePath}}',today_date)

        check_disk_space >> [infiles_path,outfiles_path]
        
        for bt in server_tasks[srv].strat_tasks:
            SubDagOperator(
                subdag=task_subdag(dag.dag_id,bt,dag.start_date, dag.schedule_interval,
                    script_path=Template('$DAG_PATH/../scripts').substitute(DAG_PATH=DAG_PATH),
                    task_info=taskMap[bt],port=get_server_port(bt,default_args['params']['telemetry_path']),default_args=default_args),
                task_id=bt)
        
        for bt in server_tasks[srv].strat_tasks:
            for dependent_task in taskMap[bt].depends:
                dag.set_dependency(dependent_task,bt)
