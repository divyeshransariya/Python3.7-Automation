from datetime import datetime,timedelta
import pendulum,logging,os,json,re
from string import Template

from nse.common.nse_tasks_config import nse_task_dict
from nse.common.varun_server_config import server_tasks
from common.make_outfiles_path import make_outfiles_path
from common.make_infiles_path import make_infiles_path
from common.remote_check_conn import remote_check_conn
from common.task_subdag import task_subdag
from common.helper_functions import *

from airflow import DAG
from airflow.configuration import conf
from airflow.models import Variable

from operators.bash_operator_with_sshhook import BashOperatorwithSSHHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.subdag_operator import SubDagOperator
from operators.PythonObserverSSHOperator import PythonObserverSSHOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor

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
        'trading_dates'     : Template('$DAG_PATH/../../../../tools/etc/trading_dates').substitute(DAG_PATH=DAG_PATH),
        'baseCodePath'      : '/home/divyesh/deploy',
        'baseStorePath'     : '/home/divyesh/deploy',
        'telemetry_path'    : '/home/divyesh/git/blackbird/blackbird/infra/telemetry_messages.d',
        'task_operator_info' : {'file' : 'nse_tasks_config','package' : 'nse.common',
                                'function' : 'get_strat_task_nse_operator'}
    }
}

local_tz = pendulum.timezone('Asia/Calcutta')

# ssh_conn_varun_root = 'nse_varun_root'
ssh_conn_varun_root = 'remote_config'

for srv in server_tasks:
    dag_name='nse_varun_startup.{}'.format(srv)
    with DAG(dag_name, default_args = default_args,
            schedule_interval = '0 13 * * *', start_date = datetime(2020, 3, 16,tzinfo=local_tz),
            catchup = False) as dag:
        latest_only = LatestOnlyOperator(task_id='latest_only',dag=dag)

        copy_script_remote = BashOperatorwithSSHHook(
            task_id= 'copy_script_remote',
            remote_host=server_tasks[srv].IP,
            command_list = ['{{params.script_path}}/local/copy_taskchain_scripts.sh ','{{params.script_path}}',
                '{{params.remote_store_path}}'])

        if server_tasks[srv].has_root_access and server_tasks[srv].can_reboot:
            reboot_remote = SubDagOperator(
                subdag = remote_check_conn(dag_name,'reboot_remote', dag.start_date, dag.schedule_interval,
                    default_args=default_args,ssh_conn_id=ssh_conn_varun_root),
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

        ## check disk space
        check_disk_space=PythonObserverSSHOperator(
            task_id='check_disk_space',
            command="df -BG {{params.bashCodePath}}/outfiles/ | tail -1 | awk '{print $4}'",
            python_callable=check_remote_disk_space,
            provide_context=True,
            op_kwargs={'space' : server_tasks[srv].desired_free_space})

        ## Set buffer sizes
        set_buffer_size = BashOperatorwithSSHHook(
            task_id='set_buffer_size',
            ssh_conn_id=ssh_conn_varun_root,
            remote_host=server_tasks[srv].IP,
            command_list = ["{{params.script_path}}/local/set_verify_buffer_sizes.sh ","16"])

        setup_screen=SSHOperator(
            task_id='setup_screen',
            command='screen -dmS test sleep 1')

        latest_only >> copy_script_remote >> reboot_remote >> sync_time >> [check_disk_space,set_buffer_size]
        reboot_remote >> setup_screen

        has_cmfo_use = False
        has_cd_use = False

        ## Set network routes - metamux or arista
        assert(server_tasks[srv].conn_switch=='metamux' or server_tasks[srv].conn_switch=='arista'),'conn_switch must be one of metamux or arista'
        if server_tasks[srv].conn_switch=='metamux':
            task_id='set_metamux_varun_nse_network_routes'
        else : 
            task_id='set_varun_nse_network_routes'

        network_routes=SSHOperator(
            task_id=task_id,
            ssh_conn_id=ssh_conn_varun_root,
            command=Template('{{params.script_path}}/remote/$script $exchange_prefix $interface,$latency')
                .substitute(script=task_id+'.sh',exchange_prefix='10.42.6',interface=server_tasks[srv].interface,latency=0))
        
        ## Create infiles path
        infiles_path = make_infiles_path(default_args['ssh_conn_id'],'{{params.remote_store_path}}','{{next_ds}}')

        ## Create outfiles path
        outfiles_path = make_outfiles_path(default_args['ssh_conn_id'],'{{params.remote_store_path}}','{{next_ds}}')

        ## Tune server
        if server_tasks[srv].tune:
            tune_server=SSHOperator(
                task_id='tune_server',
                ssh_conn_id=ssh_conn_varun_root,
                command='{{params.script_path}}/remote/tune_server.sh {{params.remote_store_path}}')
        else:
            tune_server=DummyOperator(task_id='tune_dummy')
        
        check_disk_space >> [infiles_path,outfiles_path]
        set_buffer_size >> network_routes >> tune_server

        # Transfer instruments
        ## When CM instruments gen succeeds, transfer those
        cm_info=('nse_cm_instgen','nse_startup_instgen_cmfo','nse_cm_files_task_ids')
        fo_info=('nse_fo_instgen','nse_startup_instgen_cmfo','nse_fo_files_task_ids')
        cd_info=('nse_cd_instgen','nse_startup_instgen_cd','nse_cd_files_task_ids')

        task_ids=json.loads(Variable.get('task_ids', default_var='').replace("\'","\""))
        transfer_task_suffix='_transfer'

        instruments_list =[cm_info,fo_info,cd_info]

        for instrument in instruments_list:
            base_sensor = infiles_path >> ExternalTaskSensor(
                task_id=instrument[0]+'_downstream',
                external_dag_id=instrument[1],
                external_task_id= instrument[0],
                mode='reschedule')
            
            # stored_files_task_ids = eval(Variable.get(instrument[2], default_var=str([])))

            stored_files_task_ids=task_ids[instrument[2]]

            for task in stored_files_task_ids:
                base_task=base_sensor
                if (task != base_sensor.external_task_id):
                    base_task = base_sensor >> ExternalTaskSensor(
                            task_id=task+'_sensor',
                            external_dag_id = instrument[1],
                            external_task_id = task,
                            mode='reschedule')
    
                base_task >> PythonOperator(
                    task_id = task + transfer_task_suffix,
                    python_callable = transfer_files,
                    provide_context=True,
                    op_kwargs = { 'task_id': task,
                        'dag_id': instrument[1],
                        'ftp_conn_id' : '{{params.ssh_conn_id}}'})

        # Run server tasks
        ## Any other custom files that need to be transferred
        for bt in server_tasks[srv].strat_tasks:
            buildMode=None
            if server_tasks[srv].buildMode:
                buildMode=server_tasks[srv].buildMode

            instance = SubDagOperator(
                subdag=task_subdag(dag_name,bt,dag.start_date, dag.schedule_interval,
                    task_info=nse_task_dict[bt],default_args=default_args),
                task_id=bt)

        for bt in server_tasks[srv].strat_tasks:
            for dependent_task in nse_task_dict[bt].depends:
                if dependent_task.startswith('__dag'):
                    assert(re.match("^__dag:.*;__task:.+",dependent_task)) ,'%s does not follow __dag:*;__task:* like mapping' %dependent_task
                    dag_info,task_info=dependent_task.split(';')
                    task_id=task_info.split(':')[1]
                    dag_id=dag_info.split(':')[1]
                    if dag_id=="":
                        dag.set_dependency(task_id,bt)
                        if (task_id == (cm_info[0]+transfer_task_suffix or fo_info[0]+transfer_task_suffix)):
                            has_cmfo_use =True 
                        if task_id == cd_info[0]+transfer_task_suffix:
                            has_cd_use =True
                    else:
                        if dag.has_task(task_id+'_downstream'):
                            dag.set_dependency(task_id+'_downstream',bt)
                        else:
                            instance=infiles_path >> ExternalTaskSensor(
                                task_id=task_id+'_downstream',
                                external_dag_id = dag_id,
                                external_task_id = task_id,
                                mode='reschedule')
                            dag.set_dependency(task_id+'_downstream',bt)
                else :
                    assert(dependent_task!=''), 'it is empty task,please give some task name'
                    dag.set_dependency(dependent_task,bt)
        
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
            provide_context=True
        )
        branching >> DummyOperator(task_id='dummy')
        branching >> latest_only
        globals()[dag_name]=dag
