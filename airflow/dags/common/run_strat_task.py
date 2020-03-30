from string import Template

# getTaskRunCmd
#
# Helper function to get task command to be run on remote server
#
# taskMap is a dictionary containing some or more of the following fields:
#   taskExec    : Path to executable relative to baseCodePath. Should be a Template and can contain $buildMode
#   onload      : Whether to use onload or not
#   exports     : All exports that need to be set. This will be a subset of list of keys from exportsMap
#   bbMode      : If any BLACKBIRD_MODE has to be set
#
# exportsMap is a dictionary containing key value pairs of supported shell exports
#   If exported var is a path (i.e VAR_NAME=SOME_PATH), SOME_PATH can be a template
#   referring to baseCodePath
#  
# baseCodePath - Path to base code directory
#
# baseStorePath - Path to storage directory
#
# buildMode - One of 'debug' or 'release'
def get_task_run_cmd(taskName,taskMap,exportsMap,baseCodePath, baseStorePath, date,**kwargs):
    
    # verifying task exists in taskMap
    if taskName not in taskMap:
        raise Exception('taskMap does not contain task named:  %s ' %taskName)
    taskInfo = taskMap[taskName]

    if 'buildMode' in kwargs and kwargs['buildMode']:
        buildMode=kwargs['buildMode']
    else:
        buildMode=taskMap[taskName].buildMode

    # Verify that 'taskExec' key is definitely present in taskInfo
    assert(taskInfo.exec_path is not None), "exec_path is not mentioned,provide it"

    # Verifying that buildMode is one of 'debug' or 'release'
    assert (buildMode=='debug' or buildMode=='release') , 'buildMode must be one of debug or release: %s' %buildMode

    # Appending all exports
    runCmd =''.join(['export ' + exportsMap[x].substitute(path=baseCodePath) + '; ' for x in taskInfo.exports])

    if taskInfo.bbMode:
        if taskInfo.bbMode.startswith("BBMODE"):
            runCmd = Template("export BLACKBIRD_MODE=$bbMode").substitute(bbMode=taskInfo.bbMode)
        else:
            raise ValueError("Wrong BBMODE provided")
    
    # getting value of onload parameter
    if taskInfo.onload is 'yes'   : onld='yesOnload'
    elif taskInfo.onload is 'no'  : onld='noOnload'
    else: onld='yesOnloadPoll'

    if '$' in taskInfo.exec_path:
        te = Template(taskInfo.exec_path)
    taskExec = te if isinstance(te, str) else te.substitute(buildMode = buildMode, baseCodePath=baseCodePath)
    cmd_with_screen = Template("screen -dmS $taskName $baseCodePath/scripts/remote/run_strat_task_helper.sh $baseStorePath $taskName $onld $date $taskExec")
    cmd_without_screen = Template("$baseCodePath/scripts/remote/run_strat_task_helper.sh $baseStorePath $taskName $onld $date $taskExec")

    if taskInfo.withScreen:
        cmdTemplate = cmd_with_screen 
    else: 
        cmdTemplate = cmd_without_screen 
    runCmd += cmdTemplate.substitute(
        taskName = taskName,
        baseCodePath = baseCodePath,
        baseStorePath = baseStorePath,
        onld = onld,
        date = date,
        taskExec = taskExec
    )
    return runCmd

