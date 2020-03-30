from dataclasses import dataclass,field
from datetime import time
from typing import List 

@dataclass
class ServerInfo:
    strat_tasks: list = field(default_factory=list)
    tune: bool = True
    desired_free_space : int = 30
    has_root_access : bool = False
    can_reboot : bool = False
    buildMode : str = ''
    interface: str = ''
    IP : str = ''

@dataclass
class TaskInfo:
    # Path string can contain $baseCodePath (base path housing code on server)
    # and $buildMode (debug or release). These will be replaced by appropriate
    # names
    exec_path: str

    depends: List[str] = field(default_factory=list)

    # Slack userID of the maintainer of this task. This ID will be mentioned in
    # the failure message sent to the relevant slack channel.
    #     To mention a user this will be of the form <@U024BE7LH>
    #     To mention a channel this will be of the form <!subteam^SAZ94GDB8>
    maintainer_slack: str = ''

    # If telemetry is true, and telemetryCheckExpr is '', we will only check if console telemetry --once works successfully
    telemetry_check: bool = False
    telemetry_check_expr: str = ''

    onload: bool = False

    buildMode : str = 'debug'
    
    exports: List[str] = field(default_factory=list)

    # Offsets from midnight (specify along with timezone information)
    startTime: time = None     # None implies start as soon as possible
    endTime: time = None       # None implies no end

    bbMode: str = ''
    withScreen: bool = True         # Why is this needed?

def convert_to_dict(obj):
    return obj.__dict__

def dict_to_obj(our_dict):
    obj = TaskInfo(**our_dict)
    return obj