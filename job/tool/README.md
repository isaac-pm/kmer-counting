# allocation-footprint.py

Shows, for any finished Slurm job, what its allocation held against what it
used, the gCO2e per run of that allocation (operational + embodied), and a
right-sized request with its own gCO2e and the `#SBATCH` lines to use.

## What it does

Given one job's accounting data it prints:

1. **Held vs used** — allocated nodes/cores and requested memory vs average
   busy cores (`TotalCPU/Elapsed`) and peak `MaxRSS`.
2. **Held footprint** — the gCO2e of running that allocation once, split into
   operational and embodied terms.
3. **Right-sized request** — `cores = max(1, ceil(TotalCPU/Elapsed))`,
   `mem = ceil(MaxRSS_GiB * 1.25)` GiB, cores then raised to
   `ceil(mem_MB / --mem-per-core-mb)` if the scheduler needs it, plus its own
   footprint and the saving vs what was held.

Method (computed per node, then scaled by `AllocNodes`):

- `energy_J = idle_w*cores/node_cores*elapsed + active_w*TotalCPU_s
  + mem_w_per_gb*mem_gb*elapsed`
- `operational_g = energy_J/3.6e6 * PUE * grid`
- `embodied_g = hardware_kg*1000 * max(cores/node_cores, mem_gb/node_mem_gb)
  * elapsed / (life_years*365.25*86400)` — here `hardware_kg` is the
  *production footprint* of one node in kgCO2e (not its mass), so
  `hardware_kg*1000` converts it to gCO2e before the per-node utilisation
  fraction and the elapsed/lifetime share are applied.

If the allocation took the whole node (`AllocCPUS == node_cores`) the whole
installed memory (`--node-mem-gb`) is counted; otherwise the requested memory
(`ReqMem`) is used.  `--node-mem-gb` and `--mem-w-per-gb` are per **GB
(decimal, i.e. 10^9 bytes)**, not GiB.

## How to run

Needs **Python 3.6 or newer** (stdlib only; no other dependencies).

```sh
# Offline, from a saved sacct dump:
python3 allocation-footprint.py --sacct ../measurements/sacct-15860349.txt

# Live, on a cluster (calls sacct itself):
python3 allocation-footprint.py --job 15860349
```

The saved file may have any number of banner/command lines before the header
line that begins with `JobID|`; they are skipped.  Extra columns are allowed.
The job row is the one whose `JobID` has no `.` step suffix.

Example output:

```sh
Allocation footprint  job 15860349  (COMPLETED)
  held : 1 nodes x 128 cores, 219 GiB requested, elapsed 369s, 374.8 CPU-s
  used : 1.0 cores (TotalCPU/Elapsed), 7.4 GiB MaxRSS
held footprint:   15.09 gCO2e  (operational 13.31 + embodied 1.78)
right-sized:      6 cores, 10 GiB  ->  0.91 gCO2e  (operational 0.83 + embodied 0.08)
saving:           14.18 gCO2e
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=10G
```

The `--ntasks=1 --cpus-per-task=N` pair makes srun start a single copy of a
single-threaded program, leaving N CPUs available to it.

## Options (defaults)

| Option | Default | Meaning / source |
|---|---|---|
| `--sacct FILE` | — | read a saved `sacct -j ID -P --format=...` output |
| `--job ID` | — | run `sacct` live for a job ID |
| `--node-cores` | 128 | installed cores per node (Aion node) |
| `--node-mem-gb` | 256 | installed memory per node, **GB (decimal)** |
| `--mem-per-core-mb` | 1750 | scheduler `MaxMemPerCPU` |
| `--idle-w` | 182.642 | node idle power, W — RAPL measurement on an Aion node |
| `--active-w` | 5.217 | marginal W per busy core — RAPL on an Aion node |
| `--mem-w-per-gb` | 0.3725 | W per **GB (decimal)** of memory — Lannelongue et al. 2021 |
| `--pue` | 1.36 | PUE — EU 2023 average |
| `--grid` | 337 | gCO2e/kWh — ecoinvent 3.11, LU |
| `--hardware-kg` | 913.7 | production footprint of one node, **kgCO2e** — Dell R7525 LCA, without SSDs |
| `--life-years` | 6 | hardware lifetime — assumption |

## When it fails

It exits non-zero with a clear message when a needed field is missing or the
job did not complete.  A saved dump made with a short format (e.g. only
`JobID,JobName,NodeList,Elapsed,State,ExitCode`) lacks `AllocNodes`,
`AllocCPUS`, `ReqMem` and `TotalCPU`, so no footprint can be computed.  The
repository file `job/measurements/probe-allocation-sacct-15861635.txt` is
exactly such a case and must fail cleanly:

```sh
python3 allocation-footprint.py --sacct ../measurements/probe-allocation-sacct-15861635.txt
# error: field 'AllocNodes' missing on job row; cannot compute footprint
```

It also fails when the job is not `COMPLETED`, when elapsed time is missing or
zero, or when the input has no `JobID|` header line.
