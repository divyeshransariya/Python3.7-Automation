from datetime import datetime, timedelta
import os,pendulum,json
import logging
from string import Template

from airflow import DAG
from airflow.models import Variable
from airflow.configuration import conf
from importlib import import_module

from nse.common.download_cm_fo_files import *
from nse.common.get_prev_date import *
from common.helper_functions import validate_dagrun

from airflow.operators.bash_operator import BashOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.sensors.external_task_sensor import ExternalTaskMarker

from operators.bash_operator_with_httphook import BashOperatorwithHttpHook
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

local_tz = pendulum.timezone('Asia/Calcutta')

default_args = {
    'owner': 'Silverleaf',
    'depends_on_past': False,
    'catchup' : False,
    'email': [],
    'email_on_failure': False,
    'email_on_retry': False,
    'email_on_sla' : False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2, seconds=30),
    #'on_failure_callback': task_fail_slack_alert,
    'params': {
        "local_store": "/usr/local/airflow/logs/run_data",
        "trading_dates": Template('$DAG_PATH/../../../../tools/etc/trading_dates').substitute(DAG_PATH=DAG_PATH),
        "script_path" :  Template('$DAG_PATH/../scripts').substitute(DAG_PATH=DAG_PATH),
        "server_config" : {"nse_varun_startup" : import_module(".varun_server_config",package='nse.common').server_tasks}
        }
}
############ USED CONNECTIONS
nse_http='nse_http'
nse_sftp='nse_iisl_sftp'
nse_cmfo_http='nse_cmfo_http'  # for VOLT file download    
    
# CM AND FO instgen tasks
with DAG('nse_startup_instgen_cmfo', default_args=default_args,
    schedule_interval="0 13 * * *", start_date = datetime(2020, 3, 16,tzinfo=local_tz)) as dag:

    branching=BranchPythonOperator(
        task_id='validate_dagrun',
        python_callable=validate_dagrun,
        op_kwargs={'task' : 'latest_only','dummy_task' : 'dummy',
                    'date' : '{{ next_ds }}', 'trading_dates' : ['{{params.trading_dates}}/nse_cm.dates']},
        provide_context=True)
    
    branching >> DummyOperator(task_id='dummy')

    latest_only = LatestOnlyOperator(task_id='latest_only', dag=dag)
    branching >> latest_only

    local_store_path = '{{ params.local_store }}/{{ next_ds }}'

    # Add the task_id of the tasks which download the files to be copied to
    # 'infiles' in the appropriate list below.
    #
    # The task should return the list of files that they want copied (so that
    # the list gets stored in an xcom). The transfer tasks will pickup the
    # file names using xcom_pull for each task_id
    cm_files_task_ids = []
    fo_files_task_ids = []

    ########
    # Download raw contracts files
    cm_security_file_sensor = cm_contract_availability_sensor(poke_interval = 300, timeout = 60*60*2)
    latest_only >> cm_security_file_sensor

    cm_contracts_dld = PythonOperator(
        task_id = 'cm_contracts_dld', provide_context = True,
        python_callable = download_cm_contracts,
        op_kwargs = { 'local_store_path': local_store_path })
    cm_files_task_ids.append(cm_contracts_dld.task_id)

    fo_contracts_dld = PythonOperator(
        task_id = 'fo_contracts_dld', provide_context = True,
        python_callable = download_fo_contracts,
        op_kwargs = { 'local_store_path': local_store_path })
    fo_files_task_ids.append(fo_contracts_dld.task_id)

    cm_streams_dld = PythonOperator(
        task_id = 'cm_streams_dld', provide_context = True,
        python_callable = download_cm_stream_files,
        op_kwargs = { 'local_store_path': local_store_path })
    cm_files_task_ids.append(cm_streams_dld.task_id)

    fo_streams_dld = PythonOperator(
        task_id = 'fo_streams_dld', provide_context = True,
        python_callable = download_fo_stream_files,
        op_kwargs = { 'local_store_path': local_store_path })
    fo_files_task_ids.append(fo_streams_dld.task_id)

    cm_security_file_sensor >> [cm_contracts_dld, fo_contracts_dld, cm_streams_dld, fo_streams_dld]

    ########
    # Download and check Banned FO securities file
    fo_secban_sensor = fo_ban_availability_sensor(timeout=60*60*3)

    get_fo_secban = BashOperatorwithHttpHook(
        task_id='get_fo_secban',
        xcom_push=True,
        http_conn_id=nse_http,
        endpoint='content/fo/fo_secban.csv',
        command_list=['{{params.script_path}}/local/download_linux_file_from_url.sh '
        , 'nse_fo_secban_{{ next_ds }}.csv'
        , '{{params.local_store}}'
        , '{{next_ds}}'])
    fo_files_task_ids.append(get_fo_secban.task_id)

    check_fo_secban = PythonOperator(
        task_id = 'check_fo_secban', provide_context = True,
        python_callable = check_fo_secban_sanity,
        op_kwargs = { 'local_store_path': local_store_path})

    cm_security_file_sensor >> fo_secban_sensor >> get_fo_secban >> check_fo_secban

    ########
    # Generate CM instruments
    nse_cm_instgen = BashOperator(
        task_id = 'nse_cm_instgen',
        xcom_push = True,
        bash_command = '{{params.script_path}}/local/make_nse_cm_instruments_files.sh ' + local_store_path + ' {{ next_ds }}')
    cm_files_task_ids.append(nse_cm_instgen.task_id)

    # Generate FO instruments
    nse_fo_instgen = BashOperator(
        task_id = 'nse_fo_instgen',
        xcom_push = True,
        bash_command = '{{params.script_path}}/local/make_nse_fo_instruments_files.sh ' + local_store_path + ' {{ next_ds }}')
    fo_files_task_ids.append(nse_fo_instgen.task_id)

    get_prev_date_cm = PythonOperator(
        task_id='get_prev_date_cm', provide_context = True,
        python_callable = get_prev_date,
        op_kwargs = { 'filename': "{{params.trading_dates}}/nse_cm.dates" , 'date' : '{{ next_ds }}'})

    get_prev_date_fo = PythonOperator(
        task_id='get_prev_date_fo', provide_context = True,
        python_callable = get_prev_date,
        op_kwargs = { 'filename': "{{params.trading_dates}}/nse_fo.dates" , 'date' : '{{ next_ds }}'})

    ########
    # Index files download
    nifty_file_sensor = sense_nifty_file(poke_interval = 300, timeout = 60*60*2)

    banknifty_file_sensor = sense_bank_nifty(poke_interval = 300, timeout = 60*60*2)

    download_index_files = BashOperatorwithSSHHook(
        task_id='download_index_files',
        xcom_push=True,
        ssh_conn_id=nse_sftp,
        command_list =['{{params.script_path}}/local/download_nse_cm_index_files.sh ',
            '{{params.local_store}}','{{next_ds}} ','{{ti.xcom_pull(task_ids="get_prev_date_cm")}}'])
    cm_files_task_ids.append(download_index_files.task_id)

    ########
    # CM volt file download
    get_previous_day_cm_volt = BashOperatorwithHttpHook(
        task_id = 'prev_day_volt_nse_cm',
        http_conn_id=nse_cmfo_http,
        endpoint="CMVOLT_{{macros.ds_format(next_ds,'%Y-%m-%d','%d%m%Y')}}.CSV",
        xcom_push=True,
        command_list = ['{{params.script_path}}/local/download_linux_file_from_url.sh '
        , 'nse_cm_volt_prev_{{ next_ds }}.csv'
        , '{{params.local_store}}'
        , '{{next_ds}}'])
    cm_files_task_ids.append(get_previous_day_cm_volt.task_id)
    
    # FO volt file download
    get_previous_day_fo_volt = BashOperatorwithHttpHook(
        task_id = 'prev_day_volt_nse_fo',
        http_conn_id=nse_cmfo_http,
        endpoint="FOVOLT_{{macros.ds_format(next_ds,'%Y-%m-%d','%d%m%Y')}}.csv",
        xcom_push=True,
        command_list = ['{{params.script_path}}/local/download_linux_file_from_url.sh '
        , 'nse_fo_volt_prev_{{ next_ds }}.csv' 
        , '{{params.local_store}}'
        , '{{next_ds}}'])
    fo_files_task_ids.append(get_previous_day_fo_volt.task_id)

    latest_only >> get_prev_date_cm
    get_prev_date_cm >> get_previous_day_cm_volt
    get_prev_date_cm >> [nifty_file_sensor , banknifty_file_sensor] >> download_index_files

    latest_only >> get_prev_date_fo
    get_prev_date_fo >> get_previous_day_fo_volt

    # CM_instgen dependency
    [cm_contracts_dld, download_index_files] >> nse_cm_instgen 

    # FO instgen dependency
    [nse_cm_instgen, fo_contracts_dld, check_fo_secban] >> nse_fo_instgen

    task_ids={
        "nse_cm_files_task_ids" : cm_files_task_ids,
        "nse_fo_files_task_ids" : fo_files_task_ids
    }

    stored_task_ids=json.loads(Variable.get('task_ids', default_var='').replace("\'","\""))
    if stored_task_ids != task_ids:
        task_ids.update(stored_task_ids)
        Variable.set("task_ids",task_ids)

    nse_dags=['nse_varun_startup']
    instruments=['cm','fo']
    for instrument in instruments:
        for d in nse_dags:
            for srv in default_args['params']['server_config'][d]:
                if instrument=='cm':
                    instgen=nse_cm_instgen
                else: instgen=nse_fo_instgen
                instgen >> ExternalTaskMarker(
                    task_id=instrument+'_'+srv+'_downstream',
                    external_dag_id=d+'.'+srv,
                    external_task_id='nse_'+instrument+'_instgen_downstream')
                  
