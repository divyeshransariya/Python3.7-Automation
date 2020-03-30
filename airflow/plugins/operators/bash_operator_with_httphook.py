from airflow.exceptions import AirflowException
from airflow.utils.decorators import apply_defaults

from airflow.operators.bash_operator import BashOperator

from airflow.hooks.http_hook import HttpHook

class BashOperatorwithHttpHook(BashOperator):
    template_fields = ('command_list','env','endpoint')
    @apply_defaults
    def __init__(
            self,
            http_conn_id,
            command_list,
            endpoint=None,
            method='GET',
            *args, **kwargs):
        assert isinstance(command_list, list), "arg commad_list should be type list, but passed:{}".format(type(command_list))
        super(BashOperatorwithHttpHook, self).__init__(bash_command="",*args, **kwargs)
        self.http_conn_id = http_conn_id
        self.command_list=command_list
        self.endpoint = endpoint
        self.method = method.upper()

    def execute(self, context):
        """
        Execute the bash command in a temporary directory
        which will be cleaned afterwards
        """
        http_hook = HttpHook(http_conn_id=self.http_conn_id, method=self.method)
        conn = http_hook.get_connection(self.http_conn_id)
        
        if not self.endpoint:
            self.log.info("Searching endpoint in Extra field of Connection --> {0}".format(self.http_conn_id))
            self.endpoint=conn.extra_dejson.get('endpoint','')

            if not self.endpoint:
                raise AirflowException("Endpoint not present in extra field in conncetion"\
                    " --> {0}".format(self.http_conn_id))
                
        
        # Check if template passed in endpoint then its rendered correctly
        if not isinstance(self.endpoint,str):
            raise AirflowException("endpoint:{0} isn't render as string".format(self.endpoint))

        # On Empty URL Thrown an exception
        if not conn.host:
            raise AirflowException("URL Missing for connection:{0}, provide URL in host".format(self.http_conn_id))
        base_url = conn.host

        # Load connection info into running command
        if not base_url.endswith('/') and not self.endpoint.startswith('/'):
            self.command_list.insert(1, '/' + self.endpoint)
        else:
            self.command_list.insert(1,self.endpoint)
        
        # In command list $1 is URL and $2 is endpoint
        self.command_list.insert(1,base_url)
        self.bash_command = " ".join(self.command_list)

        return super(BashOperatorwithHttpHook, self).execute(context)