from dataclasses import dataclass
from datetime import time
from string import Template
import json

from airflow.models import Variable

from common.server_task_info import TaskInfo
from common.get_strat_task_operator import get_strat_task_operator


def convert_to_dict(obj):
    return obj.__dict__

exportsMap={ "VELA.LD_LIB"   : Template('LD_LIBRARY_PATH=$path/curveice/etc/frontrunner/') }
nse_task_dict = {
    'NseFO.NNF': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_fo_nnf_adapter',
        ['__dag:;__task:nse_fo_instgen_transfer', '__dag:;__task:setup_screen','__dag:nse_startup_instgen_cmfo;__task:fo_contracts_dld','__dag:;__task:tune_server'],
        '',True, 'NseFO.NNF.isUp = true',
        True,'debug',['VELA.LD_LIB'],time(10,10,10),time(20,10,10))

    , 'NseFO.NNF.MockFpga': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_fo_nnf_adapter_mockfpga',
        ['__dag:;__task:nse_fo_instgen_transfer', '__dag:;__task:setup_screen','__dag:;__task:tune_server'],
        '',True, 'NseFO.NNF.isUp = true',
        True)

    , 'NseFO.NNF.Fpga': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_fo_nnf_adapter_realfpga',
        ['__dag:;__task:nse_fo_instgen_transfer', '__dag:;__task:setup_screen','__dag:;__task:tune_server'],
        '',True, 'NseFO.NNF.isUp = true',
        True)

    , 'NseFO.UdpTbt': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_fo_udp_tbt',
        ['__dag:;__task:nse_fo_instgen_transfer', '__dag:;__task:setup_screen','__dag:;__task:tune_server'],
        '',True, 'NseFO.UdpTbt.isAllLive = true',
        True)

    ,'NseCM.UdpTbt': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:nse_cm_instgen_transfer', '__dag:;__task:setup_screen','__dag:;__task:tune_server'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseFO.FUNREV': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:nse_cm_instgen_transfer', '__dag:;__task:setup_screen'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseFO.INS': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:nse_cm_instgen_transfer', '__dag:;__task:setup_screen'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseFO.MOT': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:cm_streams_dld_transfer', '__dag:;__task:setup_screen'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseFO.MSN2': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:nse_cm_instgen_transfer', '__dag:;__task:setup_screen'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseFO.TPT': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:nse_cm_instgen_transfer', '__dag:;__task:setup_screen'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseFO.BAZOOKA': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:nse_cm_instgen_transfer', '__dag:;__task:setup_screen'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseCM.NNF.Mock': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:nse_cm_instgen_transfer', '__dag:;__task:setup_screen'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseCM.COT2': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:nse_cm_instgen_transfer', '__dag:;__task:setup_screen'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseCM.COT3': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:cm_streams_dld_transfer', 'NseCM.UdpTbt', 'NseFO.UdpTbt'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    ,'NseCM.NullifierUnos': TaskInfo('$baseCodePath/nse/bin/dmd/$buildMode/fo/nse_cm_udp_tbt',
        ['__dag:;__task:cm_streams_dld_transfer', '__dag:;__task:fo_streams_dld_transfer', 'NseCM.UdpTbt', 'NseFO.UdpTbt'],
        '',True, 'NseCM.UdpTbt.isAllLive = true',
        True)

    , 'NseFO.FFA': TaskInfo('$baseCodePath/ffa/bin/dmd/debug/hit_auto_nse_fo',
        ['NseFO.NNF', 'NseFO.UdpTbt'],
        '',True, '')
    }

# get_strat_task_nse_operator
#
# returns a SSHOperator for nse which run command(task) on remote server based on provided ssh_hook,taskName etc
def get_strat_task_nse_operator(ssh_conn_id,taskName, baseCodePath, baseStorePath,date,**kwargs):
    return get_strat_task_operator(ssh_conn_id,taskName,nse_task_dict,exportsMap,baseCodePath,baseStorePath,date,**kwargs)

# Variable.set("nse_task_dict",json.dumps(nse_task_dict,default=convert_to_dict))
