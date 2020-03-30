from datetime import datetime, timedelta
import pendulum,logging,json
from string import Template

from common.helper_functions import validate_dagrun
from nse.common.download_cm_fo_files import check_sanity

from airflow import DAG
from airflow.configuration import conf
from airflow.models import Variable

from airflow.operators.bash_operator import BashOperator

from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.python_operator import PythonOperator
from operators.bash_operator_with_httphook import BashOperatorwithHttpHook

from airflow.sensors.external_task_sensor import ExternalTaskSensor
from airflow.sensors.http_sensor import HttpSensor

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
    'email_on_sla' : False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    #'on_failure_callback': task_fail_slack_alert,

    # Most tasks use the silver ssh connection
    # 'ssh_conn_id': 'nse_varun_user',
    'ssh_conn_id': 'remote_config',
    'params': {
        'script_path'       :  Template('$DAG_PATH/../scripts').substitute(DAG_PATH=DAG_PATH),
        'slack_alerts'      : 'C0HFV1WP5', # Slack ID for #ops-market
        'trading_dates'     : Template('$DAG_PATH/../../../../tools/etc/trading_dates').substitute(DAG_PATH=DAG_PATH),
        'local_logs_dir'    : '/home/divyesh/deploy'
    }
}

local_tz = pendulum.timezone('Asia/Calcutta')

############ USED CONNECTIONS
nse_http='nse_http'
nse_cmfo_http='nse_cmfo_http'  # for VOLT file download
ssh_conn_varun_root = 'remote_config'
# ssh_conn_varun_root = 'nse_varun_root'

with DAG('eod_cmfo_file_transfer', default_args=default_args,
    schedule_interval="17 12 * * *", start_date = datetime(2020, 3, 10,tzinfo=local_tz)) as dag:
    
    branching=BranchPythonOperator(
        task_id='validate_dagrun',
        python_callable=validate_dagrun,
        op_kwargs={'task' : 'latest_only','dummy_task' : 'dummy',
                    'date' : '{{ next_ds }}', 'trading_dates' : ['{{params.trading_dates}}/nse_cm.dates']},
        provide_context=True)
    
    branching >> DummyOperator(task_id='dummy')
    eod_cmfo_files_task_ids=[]

    latest_only = LatestOnlyOperator(task_id='latest_only')
    branching >> latest_only

    day="{{ macros.ds_format(next_ds,'%Y-%m-%d','%d') }}"
    month="{{ macros.ds_format(next_ds,'%Y-%m-%d','%b') | upper}}"
    year="{{ macros.ds_format(next_ds,'%Y-%m-%d','%Y') }}"
    file_path = '/content/historical/EQUITIES/'+year+'/'+month+'/cm'+day+month+year+'bhav.csv'
    
    cm_bhavcopy_sensor=HttpSensor(task_id ='cm_bhavcopy_sensor',
        endpoint = file_path+'.zip',
        http_conn_id = nse_http, method='GET',
        mode='reschedule')
    
    download_nsecm_bhavcopy = BashOperatorwithHttpHook(
        task_id = 'download_nsecm_bhavcopy',
        http_conn_id=nse_http,
        endpoint=file_path,
        xcom_push=True,
        command_list = ['{{params.script_path}}/local/download_cmfo_bhav_copies.sh '
        , 'cm'+day+month+year+'bhav.csv'
        , 'nse_cm_bhavcopy.{{ next_ds }}.csv' 
        , '{{params.local_logs_dir}}'
        , '{{next_ds}}'])
    eod_cmfo_files_task_ids.append(download_nsecm_bhavcopy.task_id)

    ########
    # CMFO Volt file sensor
    cm_volt_sensor = HttpSensor(task_id = 'cm_volt_sensor',
        endpoint = "CMVOLT_{{macros.ds_format(next_ds,'%Y-%m-%d','%d%m%Y')}}.csv",
        http_conn_id = nse_cmfo_http, method='GET',
        extra_options={'check_response':True, 'allow_redirects':False, 'timeout':60},
        mode='reschedule', timeout=60*60*3)

    fo_volt_sensor = HttpSensor(task_id = 'fo_volt_sensor',
        endpoint = "FOVOLT_{{macros.ds_format(next_ds,'%Y-%m-%d','%d%m%Y')}}.csv",
        http_conn_id = nse_cmfo_http, method='GET',
        extra_options={'check_response':True, 'allow_redirects':False, 'timeout':60},
        mode='reschedule', timeout=60*60*3)

    #########
    # CM volt file download
    get_cm_volt = BashOperatorwithHttpHook(
        task_id = 'today_volt_nse_cm',
        http_conn_id=nse_cmfo_http,
        endpoint="CMVOLT_{{macros.ds_format(next_ds,'%Y-%m-%d','%d%m%Y')}}.csv",
        xcom_push=True,
        command_list = ['{{params.script_path}}/local/download_linux_file_from_url.sh '
        , 'nse_cm_volt_{{ next_ds }}.csv' # renamed like this after downloading..
        , '{{params.local_store}}'
        , '{{next_ds}}'])
    eod_cmfo_files_task_ids.append(get_cm_volt.task_id)

    ##########
    # FO volt file download
    get_fo_volt = BashOperatorwithHttpHook(
        task_id = 'today_volt_nse_fo',
        http_conn_id=nse_cmfo_http,
        endpoint="FOVOLT_{{macros.ds_format(next_ds,'%Y-%m-%d','%d%m%Y')}}.csv",
        xcom_push=True,
        command_list = ['{{params.script_path}}/local/download_linux_file_from_url.sh '
        , 'nse_fo_volt_{{ next_ds }}.csv' # renamed like this after downloading..
        , '{{params.local_store}}'
        , '{{next_ds}}'])
    eod_cmfo_files_task_ids.append(get_fo_volt.task_id)

    check_date_cm = PythonOperator(
        task_id = 'check_date_cm', provide_context = True,
        python_callable = check_sanity,
        op_kwargs = {'file_name': 'nse_cm_bhavcopy.' ,'local_store_path': '{{params.local_logs_dir}}' , 'date' : '{{ next_ds }}'})
    download_nsecm_bhavcopy >> check_date_cm
        
    file_path='/content/historical/DERIVATIVES/'+year+'/'+month+'/fo'+day+month+year+'bhav.csv'
    fo_bhavcopy_sensor=HttpSensor(task_id ='fo_bhavcopy_sensor',
        endpoint = file_path+'.zip',
        http_conn_id = 'nse_http', method='GET',
        mode='reschedule')

    download_nsefo_bhavcopy = BashOperatorwithHttpHook(
        task_id = 'download_nsefo_bhavcopy',
        http_conn_id=nse_http,
        endpoint=file_path,
        xcom_push=True,
        command_list = ['{{params.script_path}}/local/download_bhav_copies_helper.sh '
        , 'fo'+day+month+year+'bhav.csv'
        , 'nse_fo_bhavcopy.{{ next_ds }}.csv' 
        , '{{params.local_logs_dir}}'
        , '{{next_ds}}'])
    eod_cmfo_files_task_ids.append(download_nsefo_bhavcopy.task_id)

    check_date_fo = PythonOperator(
        task_id = 'check_date_fo', provide_context = True,
        python_callable = check_sanity,
        op_kwargs = {'file_name': 'nse_fo_bhavcopy.' ,'local_store_path': '{{params.local_logs_dir}}' , 'date' : '{{ next_ds }}'})
    download_nsefo_bhavcopy >> check_date_fo

    wait_till_instgen=ExternalTaskSensor(
        task_id='wait_till_instgen',
        external_dag_id='nse_startup_instgen_cmfo',
        external_task_id= 'nse_fo_instgen',
        mode='reschedule')

    make_nsefo_bhavcopy=BashOperator(
        task_id='make_nsefo_bhavcopy',
        bash_command='{{params.script_path}}/local/make_nse_fo_bhavcopies.sh {{params.local_logs_dir}} {{ next_ds }}')   
    eod_cmfo_files_task_ids.append(make_nsefo_bhavcopy.task_id)  

    ########
    # Dependencies
    latest_only >> [ cm_bhavcopy_sensor, fo_bhavcopy_sensor, wait_till_instgen] 
    latest_only >> [ cm_volt_sensor, fo_volt_sensor]
    cm_volt_sensor >> get_cm_volt
    fo_volt_sensor >> get_fo_volt
    cm_bhavcopy_sensor >> download_nsecm_bhavcopy   
    fo_bhavcopy_sensor >> download_nsefo_bhavcopy
    [ download_nsecm_bhavcopy, download_nsefo_bhavcopy, wait_till_instgen] >> make_nsefo_bhavcopy

    task_ids={  'eod_cmfo_files_task_ids' : eod_cmfo_files_task_ids }

    stored_task_ids=json.loads(Variable.get('task_ids', default_var='').replace("\'","\""))

    if stored_task_ids != task_ids:
        task_ids.update(stored_task_ids)
        Variable.set("task_ids",task_ids)
