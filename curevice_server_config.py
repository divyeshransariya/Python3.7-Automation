
from common.server_task_info import ServerInfo

server_tasks = {
    'basildon': ServerInfo(
        strat_tasks = ['StrategyX', 'StrategyY', 'StrategyZ'],
        base_code_path = '/home/divyesh/<path you want to>',
        base_store_path = '/home/silver/<path where all logs stores>',
        desired_free_space = INF,
        has_root_access = True,
        can_reboot = True,
        build_mode = '',
        ip = '<Curveice server IP>'),
}
