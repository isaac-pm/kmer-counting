#!/bin/bash -l
#SBATCH --job-name=kmer-accounting
#SBATCH --partition=batch
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=256M
#SBATCH --time=00:05:00
#SBATCH --output=kmer-accounting-%j.log

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
jobid=${1:?baseline job ID required}
mkdir -p job/measurements

for attempt in {1..12}; do
    sacct -j "$jobid" -P \
        --format=JobID,JobName,User,Partition,NodeList,AllocNodes,AllocCPUS,ReqMem,MaxRSS,Elapsed,TotalCPU,ConsumedEnergy,ConsumedEnergyRaw,MaxDiskRead,MaxDiskWrite,State,ExitCode \
        > "job/measurements/sacct-${jobid}.txt"
    if grep -q "^${jobid}\.batch|" "job/measurements/sacct-${jobid}.txt" &&
       grep -q "^${jobid}\.0|" "job/measurements/sacct-${jobid}.txt"; then
        break
    fi
    sleep 5
done

node=$(sacct -j "$jobid" -X -n -P --format=NodeList | head -1)
if [[ "$node" == aion-* ]]; then
    scontrol show node "$node" > "job/measurements/node-${node}.txt"
fi

cp "kmer-baseline-${jobid}.log" "job/measurements/baseline-${jobid}.txt"
date -u +'%Y-%m-%dT%H:%M:%SZ' > "job/measurements/collected-${jobid}.txt"
