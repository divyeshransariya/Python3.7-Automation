from airflow.models import Variable
from string import Template

from airflow.contrib.operators.slack_webhook_operator import SlackWebhookOperator

from airflow.hooks.base_hook import BaseHook

def getlast(filename,n):
    with open(filename) as f:
        last_n = f.readlines()[-n:]
        return '```'+ "".join(last_n) +'```'
        
def task_fail_slack_alert(context):
    slack_config = Variable.get("slack_config", deserialize_json=True)
    dag=context.get('task_instance').dag_id
    slack_webhook_token = BaseHook.get_connection(slack_config[dag]).password
    log_path=context.get('task_instance').log_filepath.strip('.log')
    log_path=log_path+'/1.log'
    log_url=context.get('task_instance').log_url
    date=str(context.get('execution_date')).split('T')
    text = Template(":red_circle: Task Failed \n *Task*: $task \n *Dag*: $dag \n *Execution Date*: $exec_date \n *retry no* : $retry").substitute(
                            task=context.get('task_instance').task_id,
                            dag=context.get('task_instance').dag_id,
                            exec_date=date[0],
                            retry=context.get('task_instance').try_number)
    Block=[]
    Block.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
                    }
        } )
    Block.append(
        {
			"type": "divider"
		}
    )
    Block.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": getlast(log_path,20),
                    }
        } )
    Block.append(
        {
			"type": "divider"
		}
    )
    Block.append(
        {
            "type": "actions",
                "block_id": "actionblock",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Link"
                        },
                        "url": log_url,
				    }
			    ]
        }
    )
    failed_alert = SlackWebhookOperator(
        task_id='slack_test',
        http_conn_id='slack',
        webhook_token=slack_webhook_token,
        blocks=Block,
        username='airflow')
    return failed_alert.execute(context=context)
