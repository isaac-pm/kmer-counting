# Run the k-mer baseline on Aion

The baseline is `baseline/kc-py1.py`. It reads FASTA from standard input and prints a 31-mer count histogram. The fixed input is `data/M_abscessus_HiSeq_10M.fa.gz`. The Python code is single threaded. Reserving an entire 128-core Aion node isolates the run, but the counter still uses one core; use a shared single-core allocation unless exclusive-node measurements are required.

## Interactive full-node test

Connect with your ULHPC username and a public key registered with ULHPC:

```bash
ssh -p 8022 username@access-aion.uni.lu
```

On the Aion login node, change to the repository root. Use the `interactive` partition only for a short development test (at most two hours), then exit the shell to release the allocation:

```bash
cd /path/to/kmer-counting
salloc --partition=interactive --qos=debug --constraint=batch \
  --nodes=1 --ntasks-per-node=1 --cpus-per-task=128 \
  --exclusive --mem=0 --time=00:30:00 srun --pty bash -l
```

Once the prompt is on a compute node, check the environment and run a small functional test:

```bash
hostname
module purge
module load env/release/default
module load lang/Python
module -t list
python --version
printf '>read1\nACGTACGTACGTACGTACGTACGTACGTACG\n' |
  python job/baseline/kc-py1.py | awk '$2 != 0'
```

`module` is available on compute nodes, not Aion login nodes. The job needs only the default environment and Python modules; `gzip`, Bash, and Slurm commands are system tools.

### Full input in the interactive allocation

With the modules loaded and the prompt still on the compute node, run the full input from the repository root:

```bash
mkdir -p job/results
set -o pipefail
gzip -cd job/data/M_abscessus_HiSeq_10M.fa.gz |
  /usr/bin/time -v python job/baseline/kc-py1.py > job/results/baseline-interactive.tsv &&
  sha256sum job/results/baseline-interactive.tsv
exit
```

The histogram is `job/results/baseline-interactive.tsv`; `/usr/bin/time` prints timing and memory use to the terminal. Exiting releases the allocation. Use the `batch` partition for repeated or production runs.

## Batch run

From the repository root on the Aion login node:

```bash
sbatch job/run-baseline.sh
squeue -u "$USER"
```

The Slurm log is `kmer-baseline-JOBID.log` in the repository root and the histogram is `job/results/baseline-JOBID.tsv`. The log includes `/usr/bin/time -v` resource usage and the output SHA-256 checksum. The batch script requests one exclusive Aion node but launches exactly one Python task. Change the 30-minute limit if a future run needs longer. Batch runs belong in the `batch` partition; the `interactive` partition is for tests and development.

The one-read test should print `1` and `1` separated by a tab. A successful full run prints 255 histogram rows. Check the Slurm job's exit status with `sacct -j JOBID --format=JobID,State,ExitCode` before using the output. The Python module resolved to `lang/Python/3.11.5-GCCcore-13.2.0` during testing; use `module -t list` to record the version used for each run.

To smoke test the batch script with another compressed FASTA, set `INPUT_FASTA_GZ` in the submission environment, for example `sbatch --export=ALL,INPUT_FASTA_GZ=/path/to/small.fa.gz --time=00:10:00 job/run-baseline.sh`.

Cluster guidance: [SSH](https://hpc-docs.uni.lu/connect/ssh/), [interactive jobs](https://hpc-docs.uni.lu/jobs/interactive/), [modules](https://hpc-docs.uni.lu/environment/modules/), [launcher examples](https://hpc-docs.uni.lu/slurm/launchers/).
