#!/bin/bash -l
# Probe which energy counters an ordinary user can read on an Aion node.
# Run inside an exclusive allocation, from the repository root:
#   salloc -p interactive --qos=debug -N 1 --exclusive --time=00:15:00 srun --pty bash -l
#   bash job/probe-energy.sh
# Writes job/measurements/energy-probe-<node>.txt. Every check is read-only.

out="job/measurements/energy-probe-$(hostname -s).txt"
mkdir -p job/measurements
{
    echo "## Probe run $(date -u +'%Y-%m-%dT%H:%M:%SZ') on $(hostname -s), job ${SLURM_JOB_ID:-none}"

    echo "## 1. Slurm energy plugin (none => ConsumedEnergy stays empty)"
    scontrol show config | grep -i -E 'AcctGatherEnergyType|AcctGatherNodeFreq|JobAcctGatherType'

    echo "## 2. Kernel powercap / RAPL files and their permissions"
    ls -l /sys/class/powercap/*/energy_uj 2>&1
    for f in /sys/class/powercap/*/energy_uj; do
        [ -e "$f" ] && echo "$f: $(cat "$f" 2>&1)"
    done

    echo "## 3. perf energy events"
    cat /proc/sys/kernel/perf_event_paranoid
    perf list 2>/dev/null | grep -i -E 'power/energy' || echo "no power/energy events listed (or perf missing)"
    perf stat -a -e power/energy-pkg/ sleep 5 2>&1 | tail -n 5

    echo "## 4. Modules that could read counters"
    module avail likwid 2>&1 | grep -i likwid || echo "no likwid module"

    echo "## 5. Node power sensors (usually root only)"
    ls /sys/class/hwmon/*/power*_input 2>&1 | head
    command -v ipmitool || echo "no ipmitool"
} > "$out" 2>&1
echo "Wrote $out"
