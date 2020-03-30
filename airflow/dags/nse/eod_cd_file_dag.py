from datetime import datetime, timedelta
import pendulum,logging,os,json
from string import Template

from airflow import DAG
from airflow.configuration import conf
from airflow.models import Variable

from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator
from airflow.operators.python_operator import BranchPythonOperator
from operators.bash_operator_with_httphook import BashOperatorwithHttpHook

from airflow.sensors.external_task_sensor import ExternalTaskSensor
from airflow.sensors.http_sensor import HttpSensor

from common.helper_functions import validate_dagrun

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
        'trading_dates' : Template('$DAG_PATH/../../../../tools/etc/trading_dates').substitute(DAG_PATH=DAG_PATH),
        'local_logs_dir'    : '/home/divyesh/deploy' 
    }
}

local_tz = pendulum.timezone('Asia/Calcutta')
nse_http='nse_http'

with DAG('eod_cd_file_transfer', default_args=default_args,
    schedule_interval="17 12 * * *", start_date = datetime(2020, 3, 10,tzinfo=local_tz)) as dag:
    
    branching=BranchPythonOperator(
        task_id='validate_dagrun',
        python_callable=validate_dagrun,
        op_kwargs={'task' : 'latest_only','dummy_task' : 'dummy',
                    'date' : '{{ next_ds }}', 'trading_dates' : '{{params.trading_dates}}/nse_cd.dates'},
        provide_context=True)
    
    branching >> DummyOperator(task_id='dummy')

    eod_cd_files_task_ids=[]

    latest_only = LatestOnlyOperator(task_id='latest_only', dag=dag)
    branching >> latest_only

    day="{{ macros.ds_format( next_ds ,'%Y-%m-%d','%d') }}"
    month="{{ macros.ds_format(next_ds,'%Y-%m-%d','%b') | upper}}"
    year="{{ macros.ds_format( next_ds ,'%Y-%m-%d','%Y') }}"
    curr_date="{{ macros.ds_format( next_ds ,'%Y-%m-%d','%d%m%y') }}"
    file_path = 'archives/cd/bhav/CD_Bhavcopy'+curr_date
    cd_bhavcopy_sensor=HttpSensor(task_id ='cd_bhavcopy_sensor',
        endpoint = file_path+'.zip',
        http_conn_id = nse_http, method='GET',
        mode='reschedule')
    
    download_nsecd_bhavcopy = BashOperatorwithHttpHook(
        task_id = 'download_nsecd_bhavcopy',
        http_conn_id=nse_http,
        endpoint=file_path,
        xcom_push=True,
        command_list = ['{{params.script_path}}/local/download_cd_bhav_copies.sh '
        , 'CD_Bhavcopy'+curr_date
        , 'nse_cd_fut_bhavcopy.{{ next_ds }}.csv'
        , 'nse_cd_opt_bhavcopy.{{ next_ds }}.csv'
        , 'CD_NSE_FO'+curr_date
        , 'CD_NSE_OP'+curr_date
        , '{{params.local_logs_dir}}'
        , '{{next_ds}}'])
    eod_cd_files_task_ids.append(download_nsecd_bhavcopy.task_id)    

    wait_till_instgen=ExternalTaskSensor(
        task_id='wait_till_instgen',
        external_dag_id='nse_startup_instgen_cd',
        external_task_id= 'nse_cd_instgen',
        mode='reschedule')

    make_nsecd_bhavcopy=BashOperator(
        task_id='make_nsecd_bhavcopy',
        bash_command='{{params.script_path}}/local/make_nse_cd_bhavcopies.sh {{params.local_logs_dir}} {{ next_ds }}')
    eod_cd_files_task_ids.append(make_nsecd_bhavcopy.task_id)     

    latest_only >> [ cd_bhavcopy_sensor , wait_till_instgen ]
    cd_bhavcopy_sensor >> download_nsecd_bhavcopy
    [ wait_till_instgen , download_nsecd_bhavcopy ] >> make_nsecd_bhavcopy 

    task_ids={  'eod_cd_files_task_ids' : eod_cd_files_task_ids }

    stored_task_ids=json.loads(Variable.get('task_ids', default_var='').replace("\'","\""))

    if stored_task_ids != task_ids:
        task_ids.update(stored_task_ids)
        Variable.set("task_ids",task_ids)
