from datetime import datetime, timedelta
import os,pendulum,json
import logging
from string import Template

from airflow import DAG
from airflow.models import Variable
from airflow.configuration import conf
from importlib import import_module

from nse.common.download_cd_files import *
from nse.common.get_prev_date import *
from common.helper_functions import validate_dagrun

from airflow.operators.bash_operator import BashOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.sensors.external_task_sensor import ExternalTaskMarker

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
    
with DAG('nse_startup_cd_dag', default_args=default_args,
    schedule_interval="17 12 * * *", start_date = datetime(2020, 3, 10,tzinfo=local_tz)) as dag:
    
    branching=BranchPythonOperator(
        task_id='validate_dagrun',
        python_callable=validate_dagrun,
        op_kwargs={'task' : 'latest_only','dummy_task' : 'dummy',
                    'date' : '{{ next_ds }}', 'trading_dates' : ['{{params.trading_dates}}/nse_cd.dates']},
        provide_context=True)
    
    branching >> DummyOperator(task_id='dummy')

    latest_only = LatestOnlyOperator(task_id='latest_only')
    branching >> latest_only

    local_store_path = '{{ params.local_store }}/{{ next_ds }}'

    # Add the task_id of the tasks which download the files to be copied to
    # 'infiles' in the appropriate list below.
    #
    # The task should return the list of files that they want copied (so that
    # the list gets stored in an xcom). The transfer tasks will pickup the
    # file names using xcom_pull for each task_id
    cd_files_task_ids = []

    cd_security_file_sensor = cd_contract_availability_sensor(poke_interval = 300, timeout = 60*60*2)
    latest_only >> cd_security_file_sensor

    cd_contracts_dld = PythonOperator(
        task_id = 'cd_contracts_dld', provide_context = True,
        python_callable = download_cd_contracts,
        op_kwargs = { 'local_store_path': local_store_path })
    cd_files_task_ids.append(cd_contracts_dld.task_id)

    # Generate FO instruments
    nse_cd_instgen = BashOperator(
        task_id = 'nse_cd_instgen',
        xcom_push = True,
        bash_command = '{{params.script_path}}/local/make_nse_cd_instruments_files.sh ' + local_store_path + ' {{ next_ds }}')
    cd_files_task_ids.append(nse_cd_instgen.task_id)

    cd_security_file_sensor >> cd_contracts_dld >> nse_cd_instgen

    task_ids={  "nse_cd_files_task_ids" : cd_files_task_ids }

    stored_task_ids=json.loads(Variable.get('task_ids', default_var='').replace("\'","\""))

    if stored_task_ids != task_ids:
        task_ids.update(stored_task_ids)
        Variable.set("task_ids",task_ids)
    
    nse_dags=['nse_varun_startup']
    
    for d in nse_dags:
        for srv in default_args['params']['server_config'][d]:
            nse_cd_instgen >> ExternalTaskMarker(
                task_id='cd_'+srv+'_downstream',
                external_dag_id=d+'.'+srv,
                external_task_id='nse_cd_instgen_downstream')
            