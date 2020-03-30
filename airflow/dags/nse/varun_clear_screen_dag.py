from datetime import datetime,timedelta
import pendulum,logging,os,json,re
from string import Template
from textwrap import dedent

from common.helper_functions import validate_dagrun
from nse.common.nse_tasks_config import nse_task_dict
from nse.common.varun_server_config import server_tasks

from airflow import DAG
from airflow.configuration import conf
from airflow.models import Variable

from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.subdag_operator import SubDagOperator
from airflow.operators.python_operator import BranchPythonOperator

from sensors.time_sensor import CustomTimeSensor

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
        'slack_alerts'      : 'C0HFV1WP5', # Slack ID for #ops-market
        'trading_file_path' : Template('$DAG_PATH/../../../../tools/etc/trading_dates').substitute(DAG_PATH=DAG_PATH)
    }
}

local_tz = pendulum.timezone('Asia/Calcutta')

# ssh_conn_varun_root = 'nse_varun_root'
ssh_conn_varun_root = 'remote_config' 

verify_screen=dedent("""\
    command_exist=$(screen -ls |grep "{screen}"|wc -l);
    if [ $command_exist -gt 0 ]; then echo 'Screen already running: {screen}; exiting...' && screen -XS {screen} quit;fi;""")

for srv in server_tasks:
    dag_name='nse_varun_clear_screen.{}'.format(srv)
    with DAG(dag_name, default_args = default_args,
            schedule_interval = '0 19 * * *', start_date = datetime(2020, 3, 8,tzinfo=local_tz),
            catchup = False) as dag:

        latest_only = LatestOnlyOperator(task_id='latest_only',dag=dag)
    
        cm_info=('nse_cm_instgen','nse_startup_instgen_cmfo','nse_cm_files_task_ids')
        fo_info=('nse_fo_instgen','nse_startup_instgen_cmfo','nse_fo_files_task_ids')
        cd_info=('nse_cd_instgen','nse_startup_instgen_cd','nse_cd_files_task_ids')
        has_cmfo_use = False
        has_cd_use = False
        instruments_list =[cm_info,fo_info,cd_info]
        transfer_task_suffix='_transfer'

        for bt in server_tasks[srv].strat_tasks:
            instance=BashOperator(
                task_id=bt,
                bash_command=verify_screen.format(screen=bt))
            
            if nse_task_dict[bt].endTime:
                latest_only >> CustomTimeSensor(
                    task_id=bt+'_sensor',
                    target_time=nse_task_dict[bt].endTime,
                    local_tz=local_tz,
                    mode='reschedule') >> instance
            else:
                latest_only >> instance

        for bt in server_tasks[srv].strat_tasks:
            for dependent_task in nse_task_dict[bt].depends:
                if dependent_task.startswith('__dag'):
                    assert(re.match("^__dag:.*;__task:.+",dependent_task)) ,'%s does not follow __dag:.*;__task:.+ like mapping' %dependent_task
                    dag_info,task_info=dependent_task.split(';')
                    task_id=task_info.split(':')[1]
                    dag_id=dag_info.split(':')[1]
                    if task_id in server_tasks[srv].strat_tasks:
                        if dag_id=="":
                            if nse_task_dict[task_id].endTime: 
                                dag.set_dependency(bt,task_id+'_sensor')
                            else:
                                dag.set_dependency(bt,task_id)
                        if (task_id is cm_info[0]+transfer_task_suffix) or (task_id is fo_info[0]+transfer_task_suffix):
                            has_cmfo_use =True 
                        if task_id is cd_info[0]+transfer_task_suffix:
                            has_cd_use =True
                else :
                    assert(dependent_task!=''), 'it is an empty task,please give some task name'
                    if dependent_task in server_tasks[srv].strat_tasks:
                        if nse_task_dict[dependent_task].endTime: 
                                dag.set_dependency(bt,dependent_task+'_sensor')
                        else:
                            dag.set_dependency(bt,dependent_task)
        
        trading_dates=[]
        if has_cmfo_use :
            trading_dates.append(default_args['params']['trading_file_path']+'/nse_cm.dates')
        if has_cd_use :
            trading_dates.append(default_args['params']['trading_file_path']+'/nse_cd.dates')
        
        branching=BranchPythonOperator(
            task_id='validate_dagrun',
            python_callable=validate_dagrun,
            op_kwargs={'task' : 'latest_only','dummy_task' : 'dummy',
                        'date' : '{{ next_ds }}', 'trading_dates' : trading_dates},
            provide_context=True)
            
        branching >> DummyOperator(task_id='dummy')
        branching >> latest_only

        globals()[dag_name]=dag
