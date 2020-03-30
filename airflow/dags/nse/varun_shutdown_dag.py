from datetime import datetime,timedelta
import pendulum,logging,os,json,re
from string import Template

from nse.common.nse_tasks_config import nse_task_dict
from nse.common.varun_server_config import server_tasks
from common.remote_check_conn import remote_check_conn
from common.helper_functions import *

from airflow import DAG
from airflow.configuration import conf
from airflow.models import Variable

from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.subdag_operator import SubDagOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
from operators.bash_operator_with_sshhook import BashOperatorwithSSHHook

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
    'owner': 'Silverleaf',
    'depends_on_past': False,
    'catchup' : False,
    'email': ['ops@silverleafcaps.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'email_on_sla' : True,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    #'on_failure_callback': task_fail_slack_alert,

    # Most tasks use the silver ssh connection
    # 'ssh_conn_id': 'nse_varun_user',
    'ssh_conn_id': 'remote_config',
    'params': {
        'script_path'       :  Template('$DAG_PATH/../scripts').substitute(DAG_PATH=DAG_PATH),
        'slack_alerts'      : 'C0HFV1WP5', # Slack ID for #ops-market
        'remote_store_path' : '/home/divyesh/tmp',
        'trading_dates'     :  Template('$DAG_PATH/../../../../tools/etc/trading_dates').substitute(DAG_PATH=DAG_PATH)
    }
}

local_tz = pendulum.timezone('Asia/Calcutta')

# ssh_conn_varun_root = 'nse_varun_root'
ssh_conn_varun_root = 'ssh_divyesh'
         
for srv in server_tasks:
    dag_name='nse_varun_shutdown.{}'.format(srv)
    with DAG(dag_name, default_args = default_args,
            schedule_interval = '17 12 * * *', start_date = datetime(2020, 3, 10,tzinfo=local_tz)) as dag:
        latest_only = LatestOnlyOperator(task_id='latest_only')

        cm_info=('nse_cm_instgen','nse_startup_instgen_cmfo','nse_cm_files_task_ids')
        fo_info=('nse_fo_instgen','nse_startup_instgen_cmfo','nse_fo_files_task_ids')
        cd_info=('nse_cd_instgen','nse_startup_instgen_cd','nse_cd_files_task_ids')
        transfer_task_suffix='_transfer'
        has_cmfo_use=False
        has_cd_use=False

        for bt in server_tasks[srv].strat_tasks:
            for dependent_task in nse_task_dict[bt].depends:
                if dependent_task.startswith('__dag'):
                    assert(re.match("^__dag:.*;__task:.+",dependent_task)) ,'%s does not follow __dag:*;__task:* like mapping' %dependent_task
                    dag_info,task_info=dependent_task.split(';')
                    task_id=task_info.split(':')[1]
                    if (task_id == (cm_info[0]+transfer_task_suffix or fo_info[0]+transfer_task_suffix)):
                        has_cmfo_use =True 
                    if task_id == cd_info[0]+transfer_task_suffix:
                        has_cd_use =True
                   
        trading_dates=[]
        if has_cmfo_use :
            trading_dates.append(default_args['params']['trading_dates']+'/nse_cm.dates')
        if has_cd_use :
            trading_dates.append(default_args['params']['trading_dates']+'/nse_cd.dates')

        branching=BranchPythonOperator(
            task_id='validate_dagrun',
            python_callable=validate_dagrun,
            op_kwargs={'task' : 'latest_only','dummy_task' : 'dummy',
                        'date' : '{{ next_ds }}', 'trading_dates' : trading_dates},
            provide_context=True)

        branching >> DummyOperator(task_id='dummy')
        branching >> latest_only

        wait_till_clear_screen=ExternalTaskSensor(
            task_id='wait_till_clear_screen',
            external_dag_id = 'nse_varun_clear_screen.{}'.format(srv),
            external_task_id = None,
            mode='reschedule')

        copy_script_remote = BashOperatorwithSSHHook(
            task_id= 'copy_script_remote',
            remote_host=server_tasks[srv].IP,
            command_list = ['{{params.script_path}}/local/copy_taskchain_scripts.sh ','{{params.script_path}}',
                '{{params.remote_store_path}}'])

        if server_tasks[srv].has_root_access and server_tasks[srv].can_reboot:
                reboot_remote = SubDagOperator(
                    subdag = remote_check_conn(dag_name,'reboot_remote', dag.start_date, dag.schedule_interval,
                        default_args=default_args,ssh_conn_id = ssh_conn_varun_root),
                    task_id = 'reboot_remote')
        else:
            reboot_remote=DummyOperator(task_id='reboot_dummy')

        ## Sync time
        if server_tasks[srv].has_root_access:
            sync_time = BashOperatorwithSSHHook(
                task_id = 'sync_time',
                ssh_conn_id =ssh_conn_varun_root,
                remote_host=server_tasks[srv].IP,
                command_list = ['{{params.script_path}}/local/sync_time.sh '],
                dag=dag)
        else:
            sync_time=DummyOperator(task_id='sync_dummy')

        transfer_task_suffix='_transfer'

        cmfo_info=('eod_cmfo_file_dag','eod_cmfo_files_task_ids')
        cd_info=('eod_cd_file_dag','eod_cd_files_task_ids')

        List=[cmfo_info,cd_info]
        for var in List: 
            stored_files_task_ids=json.loads(Variable.get('task_ids', default_var='').replace("\'","\""))[var[1]]
            for task in stored_files_task_ids:
                base_sensor = sync_time >> ExternalTaskSensor(
                    task_id=task+'_sensor',
                    external_dag_id = 'eod_cmfo_file_dag',
                    external_task_id = task,
                    mode='reschedule')

                base_sensor >> PythonOperator(
                    task_id = task + transfer_task_suffix,
                    python_callable = transfer_files,
                    provide_context=True,
                    op_kwargs = { 'task_id': task,
                        'dag_id': var[0],
                        'ftp_conn_id' : '{{params.ssh_conn_id}}'})

        #######
        ## zip copy infiles...
        zip_copy_infiles=SSHOperator(
            task_id='zip_copy_infiles',
            command='zip_copy_infiles.sh {{params.remote_store_path}}',
            remote_host=server_tasks[srv].IP
        )
        upload_nse_fotbt_metrics=BashOperatorwithSSHHook(
            task_id='upload_nse_fotbt_metrics',
            command_list=['{{params.script_path}}/local/run_nse_tbt_metrics.sh ','NseFO','{{params.script_path}}/local','{{params.remote_store_path}}'])
        
        upload_nse_cmtbt_metrics=BashOperatorwithSSHHook(
            task_id='upload_nse_cmtbt_metrics',
            command_list=['{{params.script_path}}/local/run_nse_tbt_metrics.sh ','NseCM','{{params.script_path}}/local','{{params.remote_store_path}}'])  

        upload_nse_cdtbt_metrics=BashOperatorwithSSHHook(
            task_id='upload_nse_cdtbt_metrics',
            command_list=['{{params.script_path}}/local/run_nse_tbt_metrics.sh ','NseCD','{{params.script_path}}/local','{{params.remote_store_path}}']) 
        
        clear_infiles=BashOperatorwithSSHHook(
            task_id='clear_infiles',
            command_list=['{{params.script_path}}/local/clear_infiles.sh ','{{params.remote_store_path}}'])
        
        dag.set_dependency('make_nsefo_bhavcopy_transfer',zip_copy_infiles.task_id)
        latest_only >> wait_till_clear_screen >> copy_script_remote >> reboot_remote >> sync_time 
        sync_time >> upload_nse_fotbt_metrics >> upload_nse_cmtbt_metrics >> upload_nse_cdtbt_metrics

        globals()[dag_name]=dag
