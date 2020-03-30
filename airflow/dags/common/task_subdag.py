import logging,os,pendulum
from string import Template
from datetime import datetime,time
from textwrap import dedent
from importlib import import_module

from airflow.models import DAG
from airflow.utils.timezone import convert_to_utc

from sensors.time_sensor import CustomTimeSensor
from common.helper_functions import get_server_port

from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.hooks.sftp_hook import SFTPHook
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator

from textwrap import dedent


verify_screen=dedent("""\
    command_exist=$(ps ax|pgrep -l "$(basename '{exec_path}')"|wc -l);\
    if [ $command_exist -gt 0 ]; then echo 'Command already running: {exec_path}; exiting...' && exit 1;fi;\
    echo 'Ready to run new screen:  {screen} with command:  {exec_path}'""")

insist_screen=dedent("""\
    screen_exist=$(screen -ls |grep -i "{screen}"|wc -l);\
    if [  $screen_exist -eq 0 ]; then echo 'screen {screen} does not exist!' && exit 1;fi;\
    echo 'screen: {screen} created successfully!'""")

def verify_telemetry(baseCodePath, port, task_info, **context):
    assert 'port' == None, "Port is Missing in kwargs"  
    assert 'task_info' == None, "TaskInfo object isn't passed in keyword args"
    
    cmd=dedent("""\
        {deploy_path}/tools/bin/dmd/debug/blackbird/tools/telemetry localhost {port} --once""").format(
            deploy_path=baseCodePath, port=port)  
    
    if task_info.telemetry_check_expr:
        expr=task_info.telemetry_check_expr
        # Removing front & back white space
        expr=expr.strip()
        logging.info("Start searching expression: '{}' in telemetry server ".format(expr))
        
        key,value = expr.split('=',maxsplit=1)
        cmd += ' | grep "{key}"'.format(key=key)
        
        # # We get bytes as output from SSHOperator and decode into UTF-8 
        res = SSHOperator(do_xcom_push=True,task_id='check_test',ssh_conn_id=context['ssh_conn_id'],command=cmd).execute(context).decode('utf-8')
        
        assert isinstance(res,str), logging.error("Can't decode telemetry expr result into str from SSH Opr.")

        # Find Value in returned stream string
        res=res.split('\n')
        for val in res:
            if val and '=' in val:
                if val.split('=')[1].strip() == value.strip():
                    logging.info("Given expression found in Telemetry server... exiting!")
                    return True

        # Not Found Expr in Telemetry
        raise logging.exception("{0} not found in Telemetry".format(expr))  
    
    # in case of Telemetry Expression is None
    else:
        cmd += " > /dev/null"
        try:
            SSHOperator(task_id='tel_check_without_expr', ssh_conn_id=context['ssh_conn_id'], command=cmd).execute(context)
        except Exception as e:
            logging.error("Command: {cmd} failed!".format(cmd=cmd))
            raise logging.exception(e)

def retrieve_file(remote_path,local_path,**context):
    with SFTPHook(ftp_conn_id = context['ftp_conn_id']) as hook_sftp:
        logging.info("retrieving file : {0} -> {1}".format(remote_path,local_path))
        hook_sftp.retrieve_file(remote_full_path=remote_path , local_full_path=local_path)
    
def store_file(remote_path,local_path,**context):
    with SFTPHook(ftp_conn_id = context['ftp_conn_id']) as hook_sftp:
        logging.info("Sending file : {0} -> {1}".format(local_path,remote_path))
        hook_sftp.store_file(remote_full_path=remote_path , local_full_path=local_path)

home='/home/silver'
temp='~/temp'
infiles_path='/deploy/infiles'

def task_subdag(parent_dag_name, child_dag_name, 
                start_date,schedule_interval,
                default_args, task_info,
                *args, **kwargs):
    with DAG('%s.%s' % (parent_dag_name, child_dag_name),
        default_args=default_args,
        schedule_interval=schedule_interval,
        start_date=start_date) as dag:

        if task_info.startTime:
            wait_till_starttime=CustomTimeSensor(
                task_id='wait_till_starttime',
                target_time=task_info.startTime,
                local_tz=start_date.tzinfo,
                mode='reschedule')

        module=import_module("."+default_args['params']['task_operator_info']['file'],package=default_args['params']['task_operator_info']['package'])
        get_strat_task_operator=getattr(module,default_args['params']['task_operator_info']['function'])    

        instance=get_strat_task_operator(default_args['ssh_conn_id'],child_dag_name,'{{params.baseCodePath}}','{{params.baseStorePath}}','{{next_ds}}')

        if child_dag_name=='ice_instgen' or child_dag_name=='curve_instgen':
            if child_dag_name=='ice_instgen':
                filename='iceeu_fo.{{next_ds}}.instruments'
            else:
                filename='curve_fo.{{next_ds}}.instruments'

            transfer_to_cloud=PythonOperator(
                task_id='transfer_to_cloud',
                python_callable = retrieve_file,
                provide_context=True,
                op_kwargs = { 'remote_path' : os.path.join(home,temp,filename),
                'local_path' : os.path.join(temp,filename),
                'ftp_conn_id' : default_args['ssh_conn_id']})

            transfer_to_server=PythonOperator(
                task_id='transfer_to_server',
                python_callable = store_file,
                provide_context=True,
                op_kwargs = { 'remote_path' : os.path.join(home,infiles_path,filename),
                'local_path' : os.path.join(temp,filename),
                'ftp_conn_id' : default_args['ssh_conn_id']})
            
            instance >> transfer_to_cloud >> transfer_to_server
            instance=transfer_to_server

        if task_info.withScreen:
            sanity_check=SSHOperator(
                task_id='sanity_check',
                command=verify_screen.format(screen=child_dag_name,exec_path=task_info.exec_path)) 
            if task_info.startTime:    
                wait_till_starttime >> sanity_check >> instance
            else :
                sanity_check >> instance

            instance=instance >> SSHOperator(
                task_id='is_on_screen',
                command=insist_screen.format(screen=child_dag_name,exec_path=task_info.exec_path))
        else :
            if task_info.startTime:
                wait_till_starttime >> instance 

        if task_info.telemetry_check:
            # get port from telemetry_messages.d only if telemetry check is True 
            port=get_server_port(child_dag_name, default_args['params']['telemetry_path'])
            kwargs.update({'port': port},default_args)

            instance >> PythonOperator(
                task_id='verif_telemetry',
                provide_context=True,
                python_callable=verify_telemetry,
                op_kwargs = kwargs)
        
        globals()[parent_dag_name+'.'+ child_dag_name]=dag

        return dag