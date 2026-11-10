#!/bin/bash -l
#SBATCH --job-name=kmer-optimised
#SBATCH --partition=batch
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=10G
#SBATCH --time=00:10:00
#SBATCH --output=kmer-optimised-%j.log

set -euo pipefail

# Submit from the repository root so SLURM_SUBMIT_DIR contains job/.
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

gzip -cd "$input" | srun --ntasks=1 --cpu-bind=cores /usr/bin/time -v python "$program" > "job/results/rightsized-${SLURM_JOB_ID}.tsv"
echo "Histogram: job/results/rightsized-${SLURM_JOB_ID}.tsv"
sha256sum "job/results/rightsized-${SLURM_JOB_ID}.tsv"
