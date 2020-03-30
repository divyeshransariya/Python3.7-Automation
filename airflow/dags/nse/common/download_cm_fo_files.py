from datetime import datetime
from zipfile import ZipFile
import gzip,logging
import os,re,json
import shutil,subprocess,tempfile

from airflow.contrib.sensors.ftp_sensor import FTPSensor
from sensors.winftp_sensor import WinFTPSensor
from airflow.contrib.sensors.sftp_sensor import SFTPSensor
from airflow.sensors.http_sensor import HttpSensor

from common.helper_functions import _download_dos_files_from_ftp

########################################
# Connection names used in this file
########################################
ftp_conn_nse_fo = 'nse_fo_ftp'
ftp_conn_nse_cm = 'nse_cm_ftp'
sftp_conn_nse_iisl = 'nse_iisl_sftp'
http_conn_nse_web = 'nse_http'

def cm_contract_availability_sensor(**kwargs):
    cm_file_path='/faoftp/faocommon/security.gz'
    return WinFTPSensor(task_id='cm_security_file_sensor',
        path=cm_file_path,
        ftp_conn_id=ftp_conn_nse_fo,
        fail_on_transient_errors = False,
        mode='reschedule', **kwargs)

def download_cm_contracts(local_store_path, **kwargs):
    suffix = kwargs['next_ds'] + '.csv'
    cm_file_pairs_gzipped = [ ['/faoftp/faocommon/security.gz', 'nse_cm_security_' + suffix] ]

    cm_file_pairs_gzipped = [ [x[0], os.path.join(local_store_path, x[1])] for x in cm_file_pairs_gzipped ]
    _download_dos_files_from_ftp(cm_file_pairs_gzipped, ftp_conn_nse_fo, True)

    targets = [x[1] for x in cm_file_pairs_gzipped]

    logging.info('All CM contract files downloaded successfully!')
    return json.dumps({'files' : targets })

def download_fo_contracts(local_store_path,**kwargs):
    suffix = kwargs['next_ds'] + '.csv'

    fo_file_pairs_gzipped = [
        ['/faoftp/faocommon/contract.gz', 'nse_fo_fo_contract_' + suffix],
        ['/faoftp/faocommon/spd_contract.gz', 'nse_fo_spd_contract_' + suffix] ]

    fo_file_pairs_gzipped = [ [x[0], os.path.join(local_store_path, x[1])] for x in fo_file_pairs_gzipped ]
    _download_dos_files_from_ftp(fo_file_pairs_gzipped, ftp_conn_nse_fo, True)

    targets = [x[1] for x in fo_file_pairs_gzipped]

    logging.info('All FO contract files downloaded successfully!')
    return json.dumps({'files' : targets })

def download_cm_stream_files(local_store_path, **kwargs):
    suffix = kwargs['next_ds'] + '.csv'

    cm_tbt_masters = [['/common/tbt_masters/cm_contract_stream_info.csv', 'nse_cm_contract_stream_info_' + suffix]]
    cm_tbt_masters = [ [x[0], os.path.join(local_store_path, x[1])] for x in cm_tbt_masters ]

    _download_dos_files_from_ftp(cm_tbt_masters, ftp_conn_nse_cm, False)

    logging.info('CM stream files downloaded successfully!')
    targets = [ x[1] for x in cm_tbt_masters ]
    return json.dumps({'files' : targets })

def download_fo_stream_files(local_store_path, **kwargs):
    suffix = kwargs['next_ds'] + '.csv'

    fo_tbt_masters = [
        ['/faoftp/faocommon/tbt_masters/fo_spd_contract_stream_info.csv', 'nse_fo_spd_contract_stream_info_' + suffix],
        ['/faoftp/faocommon/tbt_masters/fo_contract_stream_info.csv', 'nse_fo_contract_stream_info_' + suffix] ]

    fo_tbt_masters = [ [x[0], os.path.join(local_store_path, x[1])] for x in fo_tbt_masters ]

    _download_dos_files_from_ftp(fo_tbt_masters, ftp_conn_nse_fo, False)

    logging.info('FO stream files downloaded successfully!')
    targets = [ x[1] for x in fo_tbt_masters ]
    return json.dumps({'files' : targets })

def fo_ban_availability_sensor(**kwargs):
    ban_file_path = 'content/fo/fo_secban.csv'
    return HttpSensor(task_id = 'fo_secban_sensor',
        endpoint = ban_file_path,
        http_conn_id = http_conn_nse_web, method='GET',
        mode='reschedule', **kwargs)

def sense_nifty_file(**kwargs):
    return SFTPSensor(task_id='nifty_file_sensor',
                    path='/Nifty_50/NIFTY_50_{{ti.xcom_pull(task_ids="get_prev_date_cm")}}.zip',
                    sftp_conn_id=sftp_conn_nse_iisl,
                    mode='reschedule',**kwargs)

def sense_bank_nifty(**kwargs):
    return SFTPSensor(task_id='banknifty_file_sensor',
                    path='/Nifty_Bank/NIFTY_BANK_{{ti.xcom_pull(task_ids="get_prev_date_cm")}}.zip',
                    sftp_conn_id=sftp_conn_nse_iisl,
                    mode='reschedule',**kwargs)

def check_fo_secban_sanity(local_store_path, **kwargs):
    next_date = kwargs['next_ds']
    secban_file_path = os.path.join(local_store_path, 'nse_fo_secban_' + next_date + '.csv')
    pattern = re.compile('\d{2}-\w{3}-\d{4}')

    if os.path.exists(secban_file_path):
        with open(secban_file_path, 'r') as f:
            line = f.readline()
            try:
                extracted_date = pattern.findall(line)[0]
            except:
                raise ValueError("date is missing ban security file")
            logging.info(extracted_date)
            extracted_date = datetime.strptime(extracted_date, '%d-%b-%Y').strftime('%Y-%m-%d')
            if extracted_date == next_date:
                return "fo_secban.csv was correct!"
            raise ValueError("Execution_date is %s while fo_secban_date is %s"%(next_date, extracted_date)) 
    raise OSError("Given secban file doesn't exists")

def check_sanity(file_name,local_store_path,date,**kwargs):
    next_date = date
    file_path = os.path.join(local_store_path,file_name + next_date +'.csv')
    pattern = re.compile('\d{2}-\w{3}-\d{4}')

    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            line = f.read()
            extracted_date = pattern.findall(line)
            logging.info(extracted_date)
            for each_date in extracted_date:
                each_date = datetime.strptime(each_date, '%d-%b-%Y').strftime('%Y-%m-%d')
                if each_date == next_date:
                    return "File was correct!"
            raise ValueError("Execution_date is %s while file_date is %s"%(next_date, extracted_date)) 
    raise OSError("Given file doesn't exists")
