for strategy in server_tasks[srv].strat_tasks:
    # checking Dependency for each strat 
    for dependent_task in task_dict[strategy].depends:
        if dependent_task.startswith('__dag'):
            if not re.match("^__dag:.*;__task:.+", dependent_task):
                raise ValueError('{} does not follow __dag:.*(can be empty);__task:.+(can not be empty) like mapping, so change it in nse_task_config'.format(dependent_task))
            dag_obj, task_obj = dependent_task.split by ";"
            task_id = task id form task_obj
            dag_id = dag id form dag_obj
            if dag_id is empty :
                if task_id present in cm/fo instgen task :
                    has_cmfo_use = True
                    dag.set_dependency(tune_server.task_id, strategy) # First tune server after then startegy run
                if task_id is part of CD instgen task:
                    has_cd_use = True
                    dag.set_dependency(tune_server.task_id, strategy)
                dag.set_dependency(task_id, strategy) #First that task run from current dag then strat will run
            else:
                instance = Task_T >> ExternalTaskSensor(
                    task_id = <Task name>,
                    external_dag_id = dag_id,
                    external_task_id = task_id,
                    mode = 'reschedule')
                dag.set_dependency(task_id + '_downstream', strategy)
        else :
            # If no dependent task present then throw an error
            if dependent_task == '':
                raise ValueError('dependent_task is an empty string, please give some task name')
            # In case Start X depend on Start Y then
            if dependent_task in server_tasks[srv].strat_tasks:
                dag.set_dependency(dependent_task, strategy)
            # Here alias_dict represent alise for specific strategy, from alias task list no
            # two strategy depend on same alias list
            elif dependent_task in alias_dict :
                dag.set_dependency(alias_dict[dependent_task], strategy)
            else:
                raise ValueError('{} is not listed in strat_tasks or depedent_alias of strat_tasks of server {} please fix it'.format(dependent_task, srv))
