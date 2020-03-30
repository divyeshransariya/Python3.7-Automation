import gzip,logging,os,re,json
import tempfile,shutil,subprocess

from sensors.winftp_sensor import WinFTPSensor
from common.helper_functions import _download_dos_files_from_ftp

########################################
# Connection names used in this file
########################################
ftp_conn_nse_cd= 'nse_cd_ftp'

def cd_contract_availability_sensor(**kwargs):
    cd_file_path='cdsftp/cdscommon/cd_contract.gz'
    return WinFTPSensor(task_id='cd_security_file_sensor',
        path=cd_file_path,
        ftp_conn_id=ftp_conn_nse_cd,
        fail_on_transient_errors = False,
        mode='reschedule', **kwargs)
    
def download_cd_contracts(local_store_path, **kwargs):
    suffix = kwargs['next_ds'] + '.csv'
    cd_file_pairs_gzipped = [ ['/cdsftp/cdscommon/cd_contract.gz', 'nse_cd_fo_contract_' + suffix],
                              ['/cdsftp/cdscommon/cd_spd_contract.gz', 'nse_cd_spd_contract_' + suffix] ]

    cd_file_pairs_gzipped = [ [x[0], os.path.join(local_store_path, x[1])] for x in cd_file_pairs_gzipped ]
    _download_dos_files_from_ftp(cd_file_pairs_gzipped, ftp_conn_nse_cd, True)

    targets = [x[1] for x in cd_file_pairs_gzipped]

    logging.info('All CD contract files downloaded successfully!')
    return json.dumps({'files' : targets })

