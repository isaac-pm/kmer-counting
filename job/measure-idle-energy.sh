#!/bin/bash -l
#SBATCH --job-name=kmer-energy-idle
#SBATCH --partition=batch
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=128
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --time=00:05:00
#SBATCH --output=job/measurements/idle-%j.txt

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

echo "UTC start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Node: $(hostname -s)"
echo 'Command: perf stat -a -e power/energy-pkg/ sleep 60'
for socket in 0 1; do
    path="/sys/class/powercap/intel-rapl:${socket}"
    before[$socket]=$(cat "$path/energy_uj")
    range[$socket]=$(cat "$path/max_energy_range_uj")
done
perf stat -a -e power/energy-pkg/ sleep 60
echo "UTC end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
total=0
for socket in 0 1; do
    path="/sys/class/powercap/intel-rapl:${socket}"
    after=$(cat "$path/energy_uj")
    delta=$(( (after - before[socket] + range[socket]) % range[socket] ))
    echo "RAPL package ${socket}: before=${before[socket]} after=$after range=${range[socket]} delta=${delta} uJ"
    total=$((total + delta))
done
echo "RAPL CPU package total: $total uJ"
awk -v u="$total" 'BEGIN {printf "RAPL CPU package total: %.3f J; average: %.3f W\n", u/1000000, u/60000000}'
