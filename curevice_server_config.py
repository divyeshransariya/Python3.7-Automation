
from common.server_task_info import ServerInfo

server_tasks = {
    'basildon': ServerInfo(
        strat_tasks = ['IceEuFO.AggTbt', 'CurveFO.AggTbt','IceEuFO.Adapt', 'pbStrat', 'Ice.SoniaIRM', 'Ice.SoniaOneIRM',
            'transporter', 'sonia_transporter'],
        base_code_path = '/home/silver/deploy',
        base_store_path = '/home/silver/deploy',
        desired_free_space = 30,
        has_root_access = True,
        can_reboot = True,
        build_mode = '',
        ip = 'bas1.axxela.slf.ai'),
}
