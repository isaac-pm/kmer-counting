#!/bin/bash -l
#SBATCH --job-name=kmer-cython-build
#SBATCH --partition=batch
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1750M
#SBATCH --time=00:05:00
#SBATCH --output=kmer-cython-build-%j.log

set -euo pipefail

# Submit from the repository root so SLURM_SUBMIT_DIR contains job/.
cd "${SLURM_SUBMIT_DIR:?}"
program=job/baseline/kc-py1.py
build=job/optimised/build
cfile="$build/kc-py1.c"
exe="$build/kc-py1-cython"
test -r "$program"
mkdir -p "$build"

module purge
module load env/release/default
module load lang/Python
module load lang/Cython

echo "Node: $(hostname)"
echo "Job ID: ${SLURM_JOB_ID}"
cython --version
gcc --version | head -1
python3 --version
module -t list

# Compile the UNCHANGED source to C: embedded interpreter, language level 3.
# The frozen filename kc-py1.py contains a hyphen, which is not a valid Python
# module name; Cython derives the module name from the file name and rejects it.
# --module-name (Cython >= 3.0) supplies a valid module name without touching
# the source file.
cython --embed -3 --module-name kc_py1 "$program" -o "$cfile"
# Link into a self-contained executable with Python's cflags and embedded-ldflags.
gcc $(python3-config --cflags) "$cfile" $(python3-config --ldflags --embed) -o "$exe"

echo "SHA-256 of source:  $(sha256sum "$program" | awk '{print $1}')"
echo "SHA-256 of C file:  $(sha256sum "$cfile" | awk '{print $1}')"
echo "SHA-256 of exe:     $(sha256sum "$exe" | awk '{print $1}')"

# One-read test: a 31-base read yields a single canonical 31-mer, hist[1]=1.
one_read=$(printf '>read1\nACGTACGTACGTACGTACGTACGTACGTACG\n' | "$exe" | awk '$2 != 0')
echo "One-read test output: ${one_read}"
[[ "$one_read" == $'1\t1' ]]
echo "One-read test passed."
echo "Executable: $exe"
