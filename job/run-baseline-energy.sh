#!/bin/bash -l
#SBATCH --job-name=kmer-baseline
#SBATCH --partition=batch
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=128
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --time=00:30:00
#SBATCH --output=kmer-baseline-%j.log

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:?}"
input=${INPUT_FASTA_GZ:-job/data/M_abscessus_HiSeq_10M.fa.gz}
program=job/baseline/kc-py1.py
test -r "$input"
test -r "$program"
mkdir -p job/results

module purge
module load env/release/default
module load lang/Python

echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
python --version
module -t list

# The perf package event was unsupported on aion-0234 (2026-09-29). The
# readable package energy_uj counters provide a second, explicitly labelled
# measure around the same Python step. Both sockets are included; the modulo
# accounts for a counter wrap. This is CPU-package energy, not node energy.
gzip -cd "$input" | srun --ntasks=1 --cpu-bind=cores bash -c '
    set -u
    for socket in 0 1; do
        path="/sys/class/powercap/intel-rapl:${socket}"
        before[$socket]=$(cat "$path/energy_uj") || exit 1
        range[$socket]=$(cat "$path/max_energy_range_uj") || exit 1
    done
    start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    echo "RAPL start UTC: $start" >&2
    echo "Command: perf stat -a -e power/energy-pkg/ /usr/bin/time -v python job/baseline/kc-py1.py" >&2
    perf stat -a -e power/energy-pkg/ /usr/bin/time -v python job/baseline/kc-py1.py
    rc=$?
    end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    echo "RAPL end UTC: $end" >&2
    total=0
    for socket in 0 1; do
        path="/sys/class/powercap/intel-rapl:${socket}"
        after=$(cat "$path/energy_uj") || exit 1
        delta=$(( (after - before[socket] + range[socket]) % range[socket] ))
        echo "RAPL package ${socket}: before=${before[socket]} after=$after range=${range[socket]} delta=${delta} uJ" >&2
        total=$((total + delta))
    done
    echo "RAPL CPU package total: $total uJ" >&2
    echo "RAPL CPU package total: $(awk -v u="$total" "BEGIN {printf \"%.3f\", u/1000000}") J" >&2
    exit "$rc"
' > "job/results/baseline-${SLURM_JOB_ID}.tsv"
echo "Histogram: job/results/baseline-${SLURM_JOB_ID}.tsv"
sha256sum "job/results/baseline-${SLURM_JOB_ID}.tsv"
