from datetime import time

from common.server_task_info import TaskInfo

# For export environmental variables...
exports_map={ }

nse_tasks_dict={
    'Strategy_X': TaskInfo(exec_path='$base_code_path/< path of strat object file >/$build_mode/....',
        build_mode='release',
        depends=['__dag:;__task:task_T', '__dag:;__task:<Depends on instrument tranfer task>'],
        depend_alias=['Start Y'],
        maintainer_slack=[],
        telemetry_check_expr='<Some telemetry Expression to check strat X running correctly>',
        onload=True, start_time=<Time for when strat X will run on server>, end_time=<After this time strat X should be stop>),
}
