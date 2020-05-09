# Airflow Slack notifications

## Installation 

Make sure [slackclient v1.3.1](https://github.com/slackapi/python-slackclient/releases/tag/1.3.1) is installed (for apache-airflow 1.10).

```bash
pip install -U "apache-airflow[slack,...]"
```

## General usage

Generate a [slack legacy token](https://api.slack.com/custom-integrations/legacy-tokens) for your workspace and create a `SLACK_LEGACY_TOKEN` environmental variable.

```python
import os
from airflow.operators.slack_operator import SlackAPIPostOperator

SLACK_LEGACY_TOKEN = os.environ['SLACK_LEGACY_TOKEN']

def send_slack_notification(
    message='',
    attachments=None,
    channel=None,
):
    """Send message to Slack.

    message: Text of the message to send. See below for an explanation of
    formatting. This field is usually required, unless you're providing only
    attachments instead. Provide no more than 40,000 characters or risk truncati

    attachments: [list of max 100] dict[s] slack message attachment[s]
    see https://api.slack.com/docs/message-attachments#attachment_structure

    channel:  a channel in your workspace starting with `#`
    """
    assert isinstance(message, str) and message or attachments
    if isinstance(attachments, dict):
        attachments = [attachments]
    channel = channel or '#airflow-notifications'
    notification_operator = SlackAPIPostOperator(
        task_id='slack_notification',
        username='airflow-notifications',
        icon_url='https://github.com/apache/airflow/raw/v1-10-stable/airflow/www/static/pin_100.png',
        token=SLACK_LEGACY_TOKEN,
        channel=channel,
        text=message,
        attachments=attachments,
    )
    notification_operator.execute()
```

## Example implementation

<img width="536" alt="Failure notification" src="https://user-images.githubusercontent.com/14880945/58114709-a1e8b880-7bf8-11e9-9da1-f5fd37dd1af8.png">

Send a notification with selected [context details](https://github.com/apache/airflow/blob/v1-10-stable/airflow/models/taskinstance.py#L1168-L1206) in a [message attachment](https://api.slack.com/docs/message-attachments) when a task fails using `default_args`.

```python
default_args = {
    ...
    'on_failure_callback': failed_task_slack_notification,
}

def failed_task_slack_notification(kwargs):
    """Send failed task notification with context provided by operator."""
    domain = extract_domain(
        kwargs['ti'].log_url,
        with_subdomain=True,
    )
    dag = kwargs['ti'].dag_id
    run_id = kwargs['run_id']
    task = kwargs['ti'].task_id
    exec_date = kwargs['execution_date']
    try_number = kwargs['ti'].try_number - 1
    max_tries = kwargs['ti'].max_tries + 1
    exception = kwargs['exception']
    log_url = kwargs['ti'].log_url
    # command = kwargs['ti'].command(),

    message = (
        f'`DAG`  {dag}'
        f'\n`Run Id`  {run_id}'
        f'\n`Task`  {task} _(try {try_number} of {max_tries})_'
        f'\n`Execution`  {exec_date}'
        f'\n```{exception}```'
        # f'`Command`  {command}\n'
    )

    attachments = {
        'mrkdwn_in': ['text', 'pretext'],
        'pretext': ':boom: *Failure*',
        'title': domain.split('.')[0],
        'title_link': f'https://{domain}',
        'text': message,
        'actions': [
            {
                'type': 'button',
                'name': 'view log',
                'text': 'View log :airflow:',
                'url': log_url,
                'style': 'primary',
            },
        ],
        'color': 'danger',  # 'good', 'warning', 'danger', or hex ('#439FE0')
        'fallback': 'details',  # Required plain-text summary of the attachment
    }

    send_slack_notification(attachments=attachments)
```
