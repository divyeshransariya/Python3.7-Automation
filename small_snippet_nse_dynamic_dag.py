for bt in server_tasks[srv].strat_tasks:
for dependent_task in task_dict[bt].depends:
    if dependent_task.startswith('__dag'):
        if not re.match("^__dag:.*;__task:.+",dependent_task):
            raise ValueError('{} does not follow __dag:.*(can be empty);__task:.+(can not be empty) like mapping, so change it in nse_task_config'.format(dependent_task))
        dag_info,task_info = dependent_task.split(';')
        task_id = task_info.split(':')[1]
        dag_id = dag_info.split(':')[1]
        if dag_id == "":
            if task_id in (cm_info[0] + transfer_task_suffix, fo_info[0] + transfer_task_suffix):
                has_cmfo_use = True
                dag.set_dependency(tune_server.task_id, bt)
            if task_id == cd_info[0] + transfer_task_suffix:
                has_cd_use = True
                dag.set_dependency(tune_server.task_id, bt)
            dag.set_dependency(task_id,bt)
        else:
            if dag.has_task(task_id + '_downstream'):
                dag.set_dependency(task_id + '_downstream', bt)
            else:
                instance = infiles_path >> ExternalTaskSensor(
                    task_id = task_id + '_downstream',
                    external_dag_id = dag_id,
                    external_task_id = task_id,
                    mode = 'reschedule')
                dag.set_dependency(task_id + '_downstream', bt)
    else :
        if dependent_task == '':
            raise ValueError('dependent_task is an empty string,please give some task name')
        if dependent_task in server_tasks[srv].strat_tasks:
            dag.set_dependency(dependent_task, bt)
        elif dependent_task in alias_dict :
            dag.set_dependency(alias_dict[dependent_task], bt)
        else:
            raise ValueError('{} is not listed in strat_tasks or depedent_alias of strat_tasks of server {} please fix it'.format(dependent_task, srv))
