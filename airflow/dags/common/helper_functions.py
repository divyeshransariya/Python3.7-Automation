import logging,json,os,tempfile,shutil,gzip,subprocess

from airflow.contrib.hooks.sftp_hook import SFTPHook
from airflow.contrib.hooks.ftp_hook import FTPHook

def transfer_files(task_id, dag_id, **context):
    file_list=(context['ti'].xcom_pull(task_ids=task_id, dag_id=dag_id)).replace("\'","\"")
    if not file_list:
        raise ValueError('no file is pushed')
    file_list =json.loads(file_list)['files']
    
    remote_path = context['params']['remote_store_path']
    for file in file_list:
        with SFTPHook(ftp_conn_id = context['ftp_conn_id']) as hook_sftp:
            _, file_name = os.path.split(file)
            remote_store_path = os.path.join(remote_path, file_name)
            logging.info("Sending file : {0} -> {1}".format(file,remote_store_path))
            hook_sftp.store_file(remote_full_path=remote_store_path , local_full_path=file)
                
def _download_dos_files_from_ftp(file_pairs, ftp_conn_id, is_gzipped):
    with FTPHook(ftp_conn_id = ftp_conn_id) as hook_ftp:
        for pair in file_pairs:
            local_path, _ = os.path.split(pair[1])

            with tempfile.TemporaryFile(dir = local_path) as fh:
                logging.info("Retrieving file : {0} -> {1}".format(pair[0], pair[1]))
                hook_ftp.retrieve_file(remote_full_path=pair[0], local_full_path_or_buffer = fh)
                local_file_path_tgt = pair[1]
                if is_gzipped:
                    # Gunzip this
                    with gzip.open(fh, 'r') as f_in, open(local_file_path_tgt, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                else:
                    with open(local_file_path_tgt, 'wb') as f_out:
                        shutil.copyfileobj(fh, f_out)

                # dos2unix this
                subprocess.call([ 'dos2unix', local_file_path_tgt ])
                
def validate_dagrun(task, dummy_task, date, trading_dates, **kwargs):
    for filename in trading_dates:
        with open(filename) as file:
            if str(date) in file.read():
                return task
    return dummy_task        
         
def check_remote_disk_space(space, **context):
    res=context['ssh_cmd_output']
    remote_space=int(res.splitlines()[0].replace('G',''))
    if remote_space < space:
        raise ValueError('remote space {} is lower than required space {}'.format(remote_space,space))

def get_server_port(strat, filename):
    with open(filename) as file:
        for line in file:
            if strat in line:
                res=str(line).strip()
                return int(res.split(':')[1].split(',')[0])
    return None
