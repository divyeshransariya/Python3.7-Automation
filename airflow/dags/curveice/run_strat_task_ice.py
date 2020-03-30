from string import Template
from dataclasses import dataclass
from common.server_task_info import TaskInfo
from datetime import time

from common.get_strat_task_operator import get_strat_task_operator

#exportsMap contains path that will be exported before the task execution
exportsMap={
    "VELA.LD_LIB"   : Template('LD_LIBRARY_PATH=$path/curveice/etc/frontrunner/')
}

taskMap = {
    'ice_fo_feed'       : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/frontrunner/ice/ice_fo_feed_main',
                            ['ice_instgen'],'',False,'',True,'release',["VELA.LD_LIB"]),

    'curve_fo_feed'     : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/frontrunner/curve/curve_fo_feed_main',
                            ['curve_instgen'],'',False,'',True,'release',["VELA.LD_LIB"]),

    'ice_adapt'         : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/frontrunner/ice/adapter_main',
                            ['ice_fo_feed'],'',False,'',True,'debug',["VELA.LD_LIB"]),

    # 'curveAdapt'        : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/frontrunner/curve/adapter_main',[],'',False,'',True,'debug',["VELA.LD_LIB"]),
    
    'pbStrat'           : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/strategy/quote_main_src',
                            ['ice_adapt'],'',False,'',False,'release',["VELA.LD_LIB"]),

    'sonia_strat'       : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/strategy/quote_main_sonia_ice',
                            ['curve_fo_feed','ice_adapt'],'',False,'',False,'debug',["VELA.LD_LIB"]),

    'sonia_one'         : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/strategy/quote_main_sonia_one',
                            ['ice_adapt'],'',False,'',False,'debug',["VELA.LD_LIB"]),

    'transporter'       : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/markets/transporter/cmeice/ice/transporter_process',
                            ['infiles','outfiles'],'',False,'',False,'debug',["VELA.LD_LIB"]),

    'sonia_transporter' : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/strategy/transporter_main_sonia_ice',
                            ['transporter','ice_fo_feed'],'',False,'',False,'debug',["VELA.LD_LIB"]),

    'ice_instgen'       : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/frontrunner/ice/instruments_generator_main',
                            ['infiles','outfiles'],'',False,'',False,'debug',["VELA.LD_LIB"],None,None,'',False),
                            
    'curve_instgen'     : TaskInfo('$baseCodePath/curveice/bin/dmd/$buildMode/blackbird/frontrunner/curve/instruments_generator_main ',
                            ['infiles','outfiles'],'',False,'',False,'debug',["VELA.LD_LIB"],None,None,'',False)   
}
# get_strat_task_ice_operator
#
# returns a SSHOperator for ice which run command(task) on remote server based on provided ssh_hook,taskName etc
def get_strat_task_ice_operator ( ssh_conn_id, taskName, baseCodePath, baseStorePath, date):
    return get_strat_task_operator( ssh_conn_id, taskName, taskMap, exportsMap, baseCodePath, baseStorePath, date)
