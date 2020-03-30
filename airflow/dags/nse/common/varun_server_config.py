from dataclasses import dataclass

from common.server_task_info import ServerInfo

@dataclass
class VarunServerInfo(ServerInfo):
    conn_switch: str = 'metamux' # One of metamux or arista

server_tasks = {
    'varun10': VarunServerInfo(
        ['NseFO.UdpTbt', 'NseCM.UdpTbt', 'NseFO.NNF', 'NseFO.FUNREV'
            , 'NseFO.INS', 'NseFO.MOT', 'NseFO.MSN2', 'NseFO.TPT'
            , 'NseFO.BAZOOKA'],
            True,
            50,
            True,
            True,
            '',
            'enp6s0',
            '10.42.6.131'),

    'varun14': VarunServerInfo(
        ['NseFO.UdpTbt', 'NseCM.UdpTbt', 'NseCM.NNF.Mock', 'NseCM.COT2', 'NseCM.COT3', 'NseCM.NullifierUnos'],
        True,
        50,
        True,
        True,
        '',
        'enp6s0',
        '10.42.6.131'
        'arista',),
        
    'divyesh_pc' : VarunServerInfo(
        ['NseFO.UdpTbt', 'NseCM.UdpTbt', 'NseFO.NNF', 'NseFO.FUNREV'
            , 'NseFO.INS', 'NseFO.MOT', 'NseFO.MSN2', 'NseFO.TPT'
            , 'NseFO.BAZOOKA','NseCM.NNF.Mock', 'NseCM.COT2', 'NseCM.COT3', 'NseCM.NullifierUnos','NseFO.FFA'],True,50,True,True,'','enp6s0','10.42.6.118'
    )
}
