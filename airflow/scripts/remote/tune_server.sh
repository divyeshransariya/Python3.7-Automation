set -euo pipefail

storePath=$1

housekeeping_core=0
housekeeping_core_mask=1    # FIXME: Compute this value from the core value above instead of hardcoding
verbose=true
CPUSET_ROOT=/sys/fs/cgroup/cpuset
CGROUP_OS_HK=os_hk
CGROUP_SF_HK=sf_hk
CGROUP_SF_CRITICAL=sf_critical

verbose_printf () {
    [ "$verbose" = true ] || return 0
    local fmt="$1"
    shift
    printf -- "${fmt}\n" $@ >&2
}

pid_to_name () {
    head -n 1 /proc/$1/status | cut -f 2
}

move_task () {
    if echo $1 > $CPUSET_ROOT/${2:-}/tasks 2>/dev/null; then
        [ "$verbose" = true ] && verbose_printf "$1 ($(pid_to_name $1)): Moved to ${2:-root}"
    else
        [ "$verbose" = true ] && verbose_printf "$1 ($(pid_to_name $1)): Could not be moved to ${2:-root}"
    fi
    # Make sure to return success, even if some move failed
    return 0
}

create_cgroups(){

    local NUM_CPUS=`grep -c ^processor /proc/cpuinfo`
    local MAX_CPU_ID=$((NUM_CPUS - 1))
    local MAX_NUMA_NODE_ID=$(cat /sys/devices/system/node/has_cpu | cut -d- -f2)
    local NUM_NUMA=$((MAX_NUMA_NODE_ID + 1))

    local SF_CRIT_MASK="2-$MAX_CPU_ID"
    local SF_HK_MASK="0-1"
    if [ $NUM_NUMA -gt 1 ]
    then
        echo "Total NUMA nodes: $NUM_NUMA with Total CPUs: $NUM_CPUS"
        if [ $NUM_NUMA -gt 2 ]
        then
            echo "WARNING WARNING This method handles only One and Two NUMA Node cases WARNING WARNING"
            exit 1
        fi

        local SECOND_LAST_CPU_ID=$((MAX_CPU_ID - 1))
        SF_CRIT_MASK="2-$SECOND_LAST_CPU_ID"
        SF_HK_MASK="0-1,$MAX_CPU_ID"
    fi

    # Don't load balance at the root cgroup
    # Sub cgroups created below will automatically load balance
    echo 0 > ${CPUSET_ROOT}/cpuset.sched_load_balance

    mkdir -p ${CPUSET_ROOT}/${CGROUP_OS_HK}
    verbose_printf "created cgroup ${CGROUP_OS_HK}"
    cd ${CPUSET_ROOT}/${CGROUP_OS_HK}
    /bin/echo 0-0 > cpuset.cpus
    cat ${CPUSET_ROOT}/cpuset.mems > cpuset.mems


    mkdir -p ${CPUSET_ROOT}/${CGROUP_SF_HK}
    verbose_printf "created cgroup ${CGROUP_SF_HK}"
    cd ${CPUSET_ROOT}/${CGROUP_SF_HK}
    /bin/echo $SF_HK_MASK > cpuset.cpus
    cat ${CPUSET_ROOT}/cpuset.mems > cpuset.mems
    chown -R silver ${CPUSET_ROOT}/${CGROUP_SF_HK}


    mkdir -p ${CPUSET_ROOT}/${CGROUP_SF_CRITICAL}
    verbose_printf "created cgroup ${CGROUP_SF_CRITICAL}"
    cd ${CPUSET_ROOT}/${CGROUP_SF_CRITICAL}
    /bin/echo $SF_CRIT_MASK > cpuset.cpus
    cat ${CPUSET_ROOT}/cpuset.mems > cpuset.mems
    chown -R silver ${CPUSET_ROOT}/${CGROUP_SF_CRITICAL}
}

move_all_tasks_to_cgroup(){
    while read task
    do
        move_task $task $1
    done < "$CPUSET_ROOT/tasks"
}

function assign_irq_vec_to_core_mask {
    irq_vec=$1
    core_mask=$2

    echo "Assigning interrupt $irq_vec to Core mask $core_mask"
    set +e
    echo $core_mask > /proc/irq/$irq_vec/smp_affinity
    set -e
    if [ $? -ne 0 ]
    then
        echo "Cannot assign interrupt $irq_vec"
    fi


    echo "Assigning kernel thread for interrupt $irq_vec to Core mask $core_mask"
    for g in `pgrep "irq/$irq_vec-"`
    do
        echo "Will taskset PID $g for $irq_vec"
        taskset -p $core_mask $g
    done
}


function assign_irq_to_core_mask {
    irq_name_pattern=$1
    core_mask=$2

    for f in `cat /proc/interrupts | grep -w $irq_name_pattern | cut -f1 -d':'`
    do
        echo -n "Assigning interrupt $f for $irq_name_pattern to Core mask $core_mask from current: "
        cat /proc/irq/$f/smp_affinity
        echo $housekeeping_core_mask > /proc/irq/$f/smp_affinity
        echo "Assigning kernel thread for interrupt $f to Core mask $core_mask"
        for g in `pgrep "irq/$f-"`
        do
            echo "Will taskset PID $g for $irq_name_pattern"
            taskset -p $core_mask $g
        done
    done
}

echo "Moving all future IRQs to housekeeping core $housekeeping_core"
echo $housekeeping_core_mask > /proc/irq/default_smp_affinity
echo

echo "Move all IRQs to housekeeping core $housekeeping_core"
echo "We can later move IRQs of interest to other cores"
for dir in /proc/irq/*; do
    [ -d "$dir" ] && assign_irq_vec_to_core_mask "$(basename $dir)" $housekeeping_core_mask
done

lan_subnet_prefix="10.42"
# Move LAN IRQ to Core $housekeeping_core
lan_intf=`ifconfig | grep $lan_subnet_prefix -B1 | grep -v $lan_subnet_prefix | awk -F"[ :]" '{print $1}'`
assign_irq_to_core_mask $lan_intf $housekeeping_core_mask
echo

# Move rtc0 to Core $housekeeping_core
assign_irq_to_core_mask "rtc0" $housekeeping_core_mask
echo

# Move all usb IRQs to Core $housekeeping_core
assign_irq_to_core_mask "usb[0-9]" $housekeeping_core_mask
echo

# Move all aerdrv (Advanced Error Reporting Driver) IRQ to Core $housekeeping_core
assign_irq_to_core_mask "aerdrv" $housekeeping_core_mask
echo

# Move all acpi IRQ to Core $housekeeping_core
assign_irq_to_core_mask "acpi" $housekeeping_core_mask
echo

# Move all ahci IRQ to Core $housekeeping_core
assign_irq_to_core_mask "ahci" $housekeeping_core_mask
echo

echo "Move all RCU Offload threads to Core $housekeeping_core"
for i in `pgrep rcu[^c]`
do
    set +e
    taskset -p $housekeeping_core_mask $i
    set -e

    if [ $? -ne 0 ]
    then
        echo "Cannot assign RCU task $i"
    fi
done
echo

echo "Bind all SSHD processes (and subthreads) to Core $housekeeping_core"
for i in `pgrep sshd` ; do taskset -ap $housekeeping_core_mask $i ; done
echo

echo "Bind (all?) cgroup rules daemon to Core $housekeeping_core"
for i in `pgrep cgrulesengd`; do taskset -ap $housekeeping_core_mask $i; done
echo

mceinterval=`cat /sys/devices/system/machinecheck/machinecheck0/check_interval`
mceintervalnew=0 #0 - Disables machine check. Earlier set to: 7200
echo "Changing machinecheck interval from $mceinterval to $mceintervalnew seconds"
echo $mceintervalnew > /sys/devices/system/machinecheck/machinecheck0/check_interval
echo
#echo "Turning off machinecheck for now"
#echo

echo "Use 'performance' governor for all Cores"
for i in `cat /sys/devices/system/cpu/online | cut -f2 -d- | xargs seq 0`; do echo "performance" > /sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor; done
echo

echo "Move kernel disk write thread to Core $housekeeping_core"
if [ -e /sys/devices/virtual/workqueue/writeback/cpumask ]; then echo $housekeeping_core_mask > /sys/devices/virtual/workqueue/writeback/cpumask; fi
echo

echo "Move kernel NVME workqueues (if they exist) to Core $housekeeping_core"
if [ -e /sys/devices/virtual/workqueue/nvme-wq/cpumask ]; then         echo $housekeeping_core_mask > /sys/devices/virtual/workqueue/nvme-wq/cpumask        ;fi
if [ -e /sys/devices/virtual/workqueue/nvme-delete-wq/cpumask ]; then  echo $housekeeping_core_mask > /sys/devices/virtual/workqueue/nvme-delete-wq/cpumask ;fi
if [ -e /sys/devices/virtual/workqueue/nvme-reset-wq/cpumask ]; then   echo $housekeeping_core_mask > /sys/devices/virtual/workqueue/nvme-reset-wq/cpumask  ;fi
echo

echo "Move unbound kernel workqueues to Core $housekeeping_core"
if [ -e /sys/devices/virtual/workqueue/cpumask ]; then echo $housekeeping_core_mask > /sys/devices/virtual/workqueue/cpumask; fi
echo

CURR_VM_FREE_KBYTES=`cat /proc/sys/vm/min_free_kbytes`
VM_FREE_KBYTES_THRESH=$((50 * 1024))
if [ $CURR_VM_FREE_KBYTES -lt $VM_FREE_KBYTES_THRESH ]
then
    MULT_FACTOR=4
    NEW_VM_FREE_KBYTES=$((CURR_VM_FREE_KBYTES * MULT_FACTOR))
    # This ensures enough free pages are available and page freeing happens in kswapd context and not process context"
    echo "Increasing VM minimum free kbytes ${MULT_FACTOR}X to $NEW_VM_FREE_KBYTES"
    echo $NEW_VM_FREE_KBYTES > /proc/sys/vm/min_free_kbytes
else
    echo "System has enough free VM kbytes : $CURR_VM_FREE_KBYTES"
fi


echo "Setting swappiness to 0"
sysctl -w "vm.swappiness=0"
dirtyExpTimeMins=30
dirtyExpTimeCentiSecs=$(($dirtyExpTimeMins * 60 * 100))
echo "Setting dirty page writeback time to $dirtyExpTimeMins minutes - dirty pages older than this get written out on next scan"
sysctl -w "vm.dirty_expire_centisecs=$dirtyExpTimeCentiSecs"
dirtyGB=8
dirtyBytes=$(($dirtyGB * 1024 * 1024 * 1024))     # 8GB
echo "Setting dirty_background_bytes to $dirtyGB GB"
sysctl -w "vm.dirty_background_bytes=$dirtyBytes"
echo "Setting dirty page kernel writeback wakeup interval to 15 mins"
sysctl -w "vm.dirty_writeback_centisecs=150000"
echo "Setting dirty ratio to 80 - we want writebacks to happen using the kernel thread"
sysctl -w "vm.dirty_ratio=80"

echo

echo -n "Current vmstat interval: "
cat /proc/sys/vm/stat_interval
echo "Setting vmstat interval to 10 seconds"
echo 10 > /proc/sys/vm/stat_interval

if [ ! -d "${CPUSET_ROOT}" ]; then
    verbose_printf "${CPUSET_ROOT} doesn't exist, please make sure cgroups are mounted"
else
    create_cgroups
    move_all_tasks_to_cgroup os_hk
fi


# Restrict C-states to lowest latency
echo "Running program to restrict C-states to lowest latency in screen cstate_restrict"
screen -dmS cstate_restrict $storePath/tools/bin/dmd/debug/blackbird/tools/tuning/restrict_cpu_states

