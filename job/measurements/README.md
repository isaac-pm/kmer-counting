# HW2 baseline evidence and source register

Read and submitted on 2026-09-29 (Europe/Luxembourg). The source date below is the date the source was read, not its publication date. The course's Session 4 slide 17 gives the HW2 deadline as 2026-09-30 23:59 on Moodle and asks for the frozen HPC job plus Sections III.A and III.B.

## Frozen job and protocol

- Repository commit: `253d93ec726b82670c8f4b84da20e9528c9a59ef` ([GitHub tree](https://github.com/isaac-pm/kmer-counting/tree/253d93ec726b82670c8f4b84da20e9528c9a59ef)).
- Input: `job/data/M_abscessus_HiSeq_10M.fa.gz`, 187,693,955 bytes (`stat` on Aion); SHA-256 `dd2ef49aebabfed1574b55fd002025f29b2fda88c70b2095f5e1b3a822cee736`.
- Program: `job/baseline/kc-py1.py`; SHA-256 `4628ab8d2335fbfd0da46f54dc5e8ac9b0b32e3f9df038a7993ed72ccf9d0438`.
- Batch script: `job/run-baseline.sh`; SHA-256 `f24c898bd1ebbdd32fad39e85fe69f619bdcc66b632ac50c001ebbc675ef1b8e`.
- Five `sbatch --dependency=singleton job/run-baseline.sh` submissions: 15860349, 15860350, 15860351, 15860352, 15860353. Exact submission record: `submissions.txt`.
- Partition `batch`, QoS `normal`, one exclusive Aion node, one Python task, 128 allocated CPUs, `--mem=0`, 30 minute limit. The Python program is single threaded. The allocation is a whole node even though useful CPU work occupies roughly one core.
- The five runs were **not pinned to one node** and caches were **not explicitly dropped**. Use the saved node lists and run times to describe possible cache effects; do not label a run cold or warm without evidence.
- Each baseline has an `afterany` accounting job that copies its ignored Slurm log into `baseline-JOBID.txt`, saves all `sacct` rows in `sacct-JOBID.txt`, captures its assigned node in `node-NODE.txt`, and records the collection UTC time in `collected-JOBID.txt`. The collector code is `../collect-measurement.sh`. The ignored TSV remains on Aion; its SHA-256 is printed in the copied baseline log.

## Five-run result, 2026-09-29

All five jobs completed with exit code `0:0` on `aion-0127`, and their output TSVs have the same SHA-256: `06a32de77200121a397050e015a257953dc956b7854027a1ed73b15afc12bf42`. The accounting times include batch setup and teardown; `/usr/bin/time -v` in each copied log times the Python step separately. `timing-JOBID.txt` records submit, start and end timestamps.

| Job ID | Slurm elapsed | Python-step MaxRSS | `/usr/bin/time` peak RSS | Batch-step MaxDiskRead / MaxDiskWrite | Python-step MaxDiskRead / MaxDiskWrite |
| --- | ---: | ---: | ---: | ---: | ---: |
| 15860349 | 6:09 | 7,760,552 K | 7,748,964 kbytes | 878.72 M / 680.72 M | 680.67 M / 0.00 M |
| 15860350 | 6:02 | 7,759,932 K | 7,748,316 kbytes | 878.71 M / 680.72 M | 680.67 M / 0.00 M |
| 15860351 | 6:12 | 7,760,540 K | 7,749,032 kbytes | 878.72 M / 680.72 M | 680.67 M / 0.00 M |
| 15860352 | 6:08 | 7,759,928 K | 7,748,244 kbytes | 878.71 M / 680.72 M | 680.67 M / 0.00 M |
| 15860353 | 6:04 | 7,760,436 K | 7,749,024 kbytes | 878.71 M / 680.72 M | 680.67 M / 0.00 M |

**Median Slurm elapsed: 6:08; range: 6:02–6:12 (10 seconds).** The first run was not uniquely the slowest; the third was. All five happened to land on the same node, even though they were not pinned. Cache state was not measured or reset, so this series does not establish a cold-versus-warm effect.

Slurm recorded `AllocNodes=1`, `AllocCPUS=128`, and `ReqMem=224000M` for every baseline. The Python-step peak RSS is about 7.4 GiB if Slurm's `K` denotes KiB, **3.4%** of the reservable memory (`7,760,552 KiB / (224,000 MiB × 1,024 KiB/MiB) = 3.383%`); these are different quantities. The node record shows `CPUTot=128`, `Sockets=8` (Slurm's virtual sockets), `RealMemory=224000`, and `CurrentWatts=n/a` and `AveWatts=n/a`. ULHPC's specification separately lists two physical sockets and 256 GB installed RAM.

Every `ConsumedEnergy` and `ConsumedEnergyRaw` cell in all five `sacct` records, for the job and its `.batch`, `.extern`, and `.0` steps, is **empty**, observed 2026-09-29. This is missing telemetry, not zero joules. The disk counters count process I/O as well as storage I/O: the Python-step `MaxDiskRead` of 680.67 M closely matches the 713,674,148-byte decompressed gzip stream (680.61 MiB), and the batch-step `MaxDiskWrite` of 680.72 M is consistent with gzip writing that pipe. These are interpretations of the counters, not direct GPFS measurements. Do not add batch and Python numbers as independent storage transfers.

## Storage and I/O probe

At **2026-09-29T11:43:29Z**, from the Aion repository root, `stat -c '%s %n' job/results/baseline-15860349.tsv job/data/M_abscessus_HiSeq_10M.fa.gz` returned **1,972 bytes** for the output TSV and **187,693,955 bytes** for the compressed input. `df -hT .` and `findmnt -T .` reported filesystem **`gpfs`**, source `aiongpfs`, mounted at `/mnt/aiongpfs`; `pwd -P` located the repository in `/mnt/aiongpfs/users/ipalmamedina/kmer-counting` (the home filesystem, not scratch). Exact output and commands: `storage-facts-20260929.txt`.

The batch-step `MaxDiskRead` is about 878.72 M. Subtracting the roughly 680.61 MiB pipe stream leaves about 198.11 MiB, near the compressed input's 179.00 MiB plus **about 19 MiB of other reads** (possibly binaries, libraries, or modules). This breakdown is an **inference**, not a separate measured GPFS traffic count. Expected payload read from storage is approximately the 187,693,955-byte compressed input, plus those other files; expected output payload written to storage is approximately the 1,972-byte TSV, plus logs and filesystem metadata. Runs 2–5 used the same node and may have read the input from page cache; cache residency was not measured.

## Energy probe and node facts

On **2026-09-29T11:52:34Z**, an exclusive interactive allocation (`salloc -p interactive --qos=debug -N 1 --exclusive --time=00:15:00 srun --pty bash -l`, job `15861635`) landed on `aion-0234` because `aion-0127` was occupied. From the repository root, `bash job/probe-energy.sh` wrote `energy-probe-aion-0234.txt`. Its exact checks are in `../probe-energy.sh`. `scontrol show config | grep -i -E 'AcctGatherEnergyType|AcctGatherNodeFreq|JobAcctGatherType'` returned **`AcctGatherEnergyType = acct_gather_energy/rapl`**, a 25-second node sampling interval, and `jobacct_gather/cgroup`. This configuration does not turn the blank energy cells in the five earlier `sacct` records into measurements. At **2026-09-29T11:59:15Z**, `sacct -j 15861635 -P --format=JobID,JobName,NodeList,Elapsed,ConsumedEnergy,ConsumedEnergyRaw,State,ExitCode` also showed blank energy cells for the completed interactive allocation; see `probe-allocation-sacct-15861635.txt`.

The four `energy_uj` files under `/sys/class/powercap/intel-rapl:{0,0:0,1,1:0}/` were readable by this user (`ls -l /sys/class/powercap/*/energy_uj` and `cat` of each file). `cat /sys/class/powercap/intel-rapl:{0,1}/name` identified the two parent domains as `package-0` and `package-1`. `cat /proc/sys/kernel/perf_event_paranoid` returned `2`; `perf list` advertised `power/energy-pkg/`, but both `perf stat -a -e power/energy-pkg/ sleep 5` and the 60-second command below returned **`<not supported>`**, with no joule value. `module avail likwid` found no LIKWID module and `command -v likwid-powermeter` found no executable. `ls /sys/class/hwmon/*/power*_input` found no node power sensor; `timeout 5 ipmitool sdr type 'Power Supply'` reported that no `/dev/ipmi*` device was available. These are observations for an ordinary user on `aion-0234`, not proof that hardware sensors do not exist.

At **2026-09-29T11:53:49Z–11:54:49Z**, in the same allocation, the exact command `perf stat -a -e power/energy-pkg/ sleep 60` again returned `<not supported>`. Direct `cat /sys/class/powercap/intel-rapl:{0,1}/energy_uj` readings immediately before and after that 60-second interval increased by **5,539,813,318 µJ** and **5,177,512,901 µJ**. The arithmetic `(44848501627 - 39308688309 + 52681312193 - 47503799292) / 1000000` gives **10,717.326 J** for the two CPU packages, or **178.622 W** averaged over 60 seconds. The counters' `max_energy_range_uj` was 65,532,610,987 µJ each, so no wrap occurred during this interval. Exact command output: `idle-energy-aion-0234.txt`. This is an observed idle CPU-package reading on **aion-0234**, retained as a separate diagnostic; the final subtraction uses the reading from the same node as the five runs. EPYC Rome RAPL package energy does not measure whole-node or facility electricity.

At **2026-09-29T11:53:21Z**, inside allocation `15861635`, the exact commands `hostname -s`, `lscpu`, `free -g`, `ibstat`, and `ibv_devinfo` produced `node-facts-aion-0234.txt`. The model line was **`AMD EPYC 7H12 64-Core Processor`**: two physical sockets, 64 cores per socket, 128 CPUs total. `free -g` showed 251 GiB total memory and 224 GiB available at that instant. `ibstat` showed one active InfiniBand port at rate **100** (HDR100); `ibv_devinfo` confirmed an active InfiniBand link. These measurements describe `aion-0234`; the earlier baseline `scontrol` files describe `aion-0127`.

At **2026-09-29T11:56:42Z**, five runs using the new `../run-baseline-energy.sh` were submitted with the exact command `sbatch --parsable --dependency=singleton -w aion-0127 job/run-baseline-energy.sh`; after each, `sbatch --parsable --dependency=afterany:JOBID job/collect-measurement.sh JOBID` scheduled the accounting collector. IDs are **15861652, 15861654, 15861656, 15861658, 15861660**; exact submissions and source hashes are in `energy-submissions-20260929.txt`. The new script keeps the baseline program and batch resource settings; it tries the requested `perf` wrapper and separately reads both package `energy_uj` counters around the Python step because `perf` supplies no joules on the probed node. At **2026-09-29T12:00:21Z**, `sbatch --parsable --dependency=afterany:15861660 -w aion-0127 job/measure-idle-energy.sh` queued a 60-second idle reading after run 5 (job `15861674`); see `same-node-idle-submission-20260929.txt`.

At **2026-09-29T12:35:59Z**, with `aion-0127` still occupied, `scontrol show node aion-0127` and `scontrol show node aion-0144` confirmed both nodes have 128 Slurm CPUs, 224000M reservable memory, and the `epyc,batch` features. [ULHPC's Aion compute specification](https://hpc-docs.uni.lu/systems/aion/compute/) identifies all 354 regular nodes as dual EPYC 7H12 systems with 256 GB installed RAM. The exact command `scontrol update JobId=JOBID ReqNodeList=aion-0144` was applied to each of the five pending run IDs and idle job `15861674`; see `energy-retarget-20260929.txt`. This retains the same-node design while targeting a node whose current allocation was scheduled to end earlier. At **2026-09-29T12:37:36Z**, `squeue --start -j 15861652 -o '%i|%T|%S|%R'` estimated the first run at **15:27:10 Luxembourg time** (13:27:10 UTC), about one hour earlier than the previous estimate on `aion-0127`. This was a scheduler estimate; the actual node and times are in the completed-series section below. The final subtraction uses the same-node idle reading `15861674`, not the `aion-0234` idle rate.

### Completed energy series

The five runs completed on **aion-0144** between **2026-09-29T12:46:27Z and 13:16:40Z**. The exact Python-step command in `../run-baseline-energy.sh` was `perf stat -a -e power/energy-pkg/ /usr/bin/time -v python job/baseline/kc-py1.py`, inside `srun` with `gzip -cd job/data/M_abscessus_HiSeq_10M.fa.gz` supplying standard input. `perf` reported `<not supported>` in all five logs. The script's `cat /sys/class/powercap/intel-rapl:{0,1}/energy_uj` readings before and after that step supplied the energy differences below, with counter-wrap correction using each `max_energy_range_uj`. The unmodified Python source, input, batch resource settings, and histogram hash matched the original baseline; the added measurement wrapper and node are the differences. All five Slurm jobs finished `COMPLETED`, `0:0`; `ConsumedEnergy` and `ConsumedEnergyRaw` remained empty in their `sacct` records.

| Job ID | UTC step start–end | Slurm elapsed | Perf elapsed (s) | Both CPU packages (J) | Idle-subtracted packages (J) |
| --- | --- | ---: | ---: | ---: | ---: |
| 15861652 | 12:46:27–12:52:28 | 6:04 | 360.711 | 67,833.833 | 1,952.865 |
| 15861654 | 12:52:30–12:58:27 | 5:59 | 357.814 | 67,214.859 | 1,862.977 |
| 15861656 | 12:58:29–13:04:27 | 5:59 | 357.580 | 67,128.799 | 1,819.599 |
| 15861658 | 13:04:29–13:10:32 | 6:05 | 362.740 | 67,941.415 | 1,689.864 |
| 15861660 | 13:10:33–13:16:40 | 6:08 | 366.384 | 68,827.187 | 1,910.100 |

The same-node idle job `15861674` ran **2026-09-29T13:16:41Z–13:17:41Z** on `aion-0144`. Its exact command was `perf stat -a -e power/energy-pkg/ sleep 60`, bracketed by `cat` readings of both package `energy_uj` files. `perf` again reported `<not supported>`. The direct counters increased by **10,958.712479 J** over **60.001023582 s**, giving **182.642092 W**. Source files: `idle-15861674.txt` and `idle-sacct-15861674.txt` (accounting read **2026-09-29T13:18:22Z**). The latter again has blank Slurm energy fields.

At **2026-09-29T13:19:15Z**, the exact command `python3 job/measurements/energy-calculation.py` produced `energy-summary-20260929.txt` from the copied logs, `sacct` records and idle file. It computes each incremental package value as `run package J − (10,958.712479 J / 60.001023582 s) × perf elapsed s`. **Median measured CPU-package energy: 67,833.833 J; median idle-subtracted CPU-package energy: 1,862.977 J.** The latter is a counterfactual estimate that assumes the subsequent idle power would have held during every run. It is not the job's total energy, because the exclusive node still draws the idle component while the job holds it. Neither RAPL figure includes all node components or the facility; PUE and any omitted hardware remain separate modelling choices. The new series' median Slurm elapsed is **6:04**, compared with **6:08** in the original baseline series; cache state was not controlled.

For a transparent full-node energy substitute, Lannelongue's Section 5 formula can be evaluated with the original 368-second median, the documented 280 W CPU TDP / 64 cores, 256 GB installed memory, its 0.3725 W/GB memory coefficient, and the declared PUE 1.36. Counting one active core gives **0.014 kWh of modelled site electricity**; applying full TDP to all 128 allocated cores gives **0.091 kWh**. These are sensitivity scenarios, not measurements or guaranteed bounds: the first omits idle CPU, board, storage and fabric power, while the second treats all cores as fully active despite the serial Python code. The new RAPL series supersedes a CPU-package estimate from this formula, but whole-node electricity still needs a source or explicit model for the unmeasured components.

## How to read the accounting

- `Elapsed`, `AllocNodes`, `AllocCPUS`, and `NodeList` describe the allocated resource and occupancy. `ReqMem` is Slurm's reservable memory, not necessarily the node's physical RAM. A live accounting row for the first job reported `224000M`; the Aion hardware page specifies 256 GB physically.
- Read `MaxRSS` on the Python step (`JOBID.0`) and compare it with `Maximum resident set size` in `baseline-JOBID.txt`. `MaxRSS` is a peak, not total memory allocated.
- Check both `JOBID.batch` and `JOBID.0` for `MaxDiskRead` and `MaxDiskWrite`: `gzip` runs in the batch shell and Python reads a pipe. These counters may not represent all file system traffic or page-cache hits.
- Inspect `ConsumedEnergy` and `ConsumedEnergyRaw` on every step, including blanks or zeros. Neither is an energy measurement until a nonzero counter with defined units is established.
- Verify `State` and `ExitCode` for all runs. Compare TSV hashes and all five elapsed times; report the median and range.

## Source register for III.B and later calculations

| Quantity | Source read 2026-09-29 | Evidence and limits |
| --- | --- | --- |
| Aion node | [ULHPC Aion compute nodes](https://hpc-docs.uni.lu/systems/aion/compute/) | Two physical AMD EPYC 7H12 sockets, 64 cores and 280 W TDP per CPU; 128 cores and 256 GB DDR4 3200 memory per node. Slurm exposes eight virtual sockets. Aion uses BullSequana X2410 blades, HDR100 InfiniBand, and a 480 GB local SSD. TDP is not measured energy. |
| Shared storage and interconnect | [ULHPC Aion overview](https://hpc-docs.uni.lu/systems/aion/), [interconnect](https://hpc-docs.uni.lu/systems/aion/interconnect/), [GPFS](https://hpc-docs.uni.lu/filesystems/gpfs/) | Home is on shared GPFS/SpectrumScale; Aion has a 12 switch HDR100 fabric. This job has one compute node, so no node-to-node application communication is claimed; storage I/O still crosses the fabric. Component energy and embodied shares are not available from these pages. |
| Site PUE proxy | [European Commission, DG Energy, *Assessment of the energy performance and sustainability of data centres in EU: First technical report* (July 2025), Figure 6, p. 34](https://data.europa.eu/doi/10.2833/3168794) | EU average PUE **1.36** for **2023 data**, reported in 2024 (weighted by total energy consumption, n = 681; also Table 23, p. 80). Declared as a *regional proxy*, since Session 3 says the centre publishes no Aion PUE. It is not a measurement of the University of Luxembourg site. |
| Energy substitute, if Slurm has no usable value | [Lannelongue et al., *Green Algorithms* (2021), Section 5, Experimental Section](https://doi.org/10.1002/advs.202100707) | Equation (1): `E[kWh] = t[h] * (n_c * P_c[W] * u_c + n_m[GB] * P_m[W]) * PUE / 1000`. Paper gives 0.3725 W/GB for memory and discusses TDP as a processor power proxy. Its model omits motherboard, storage, and idle power of cores excluded through `u_c`; care is needed for an exclusive 128 core allocation running one Python process. |
| Server embodied-impact candidate | [Sphera Solutions for Dell, *Life Cycle Assessment – Dell Servers R6515, R7515, R6525, R7525*, v1.0 (February 2021), Table 4-5, p. 47](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/full-lca-of-dell-severs-r6515-r7515-r6525-r7525.pdf) and [R7525 specification](https://i.dell.com/sites/csdocuments/Product_Docs/en/PowerEdge-R7525-Spec-Sheet.pdf) | Dell reports **1,768.4 kg CO2e** for production of the assessed two-socket AMD EPYC R7525, including **854.7 kg** for its two 4 TB SSDs. Aion has one 480 GB local SSD and uses a liquid-cooled three-node blade. **Do not use 1,768.4 kg as Aion's measured footprint:** the Dell LCA uses IPCC 2013 GWP100 rather than the course's IPCC 2021 convention, and its hardware differs. It is a documented proxy candidate; the choice between it and the ecoinvent dataset is made in Section III.C (HW3). |
| ecoinvent 3.11 cut-off (signed in) | `ecoinvent-lookup.txt`; [dataset 3193](https://ecoquery.ecoinvent.org/3.11/cutoff/dataset/3193/impact_assessment) | Signed-in searches for `server` (58 activities, 32 products), `computer production`, `computer, desktop` and `computer, laptop` found no server production activity. Closest: *computer production, desktop, without screen* (GLO, 221 kg CO2-eq per unit, IPCC 2021 GWP100, includes disposal) and *computer production, laptop* (GLO, 170 kg CO2-eq per unit). ecoinvent 3.11 was released on 20 November 2024. |
| Grid factor (read 2026-10-19) | `ecoinvent-lookup.txt`, Dataset 3; [dataset 2297](https://ecoquery.ecoinvent.org/3.11/cutoff/dataset/2297/impact_assessment) | ecoinvent 3.11 cut-off, *market for electricity, low voltage*, LU, 2020–2024, IPCC 2021 climate change total (excl. biogenic CO2), GWP100: **337 gCO2e/kWh**. Electricity consumed in Luxembourg, imports and grid losses included. Used by `lcia-calculation.py`, whose output is `lcia-summary-20261019.txt`. |
| Service life | [ULHPC Aion timeline](https://hpc-docs.uni.lu/systems/aion/timeline/) and [Dell R7525 PCF](https://www.delltechnologies.com/asset/en-us/products/servers/briefs-summaries/poweredge-r7525-pcf-report.pdf) | Aion entered production in October–November 2021 and is still operating in September 2026, so Dell's four-year modelling lifetime for a different server cannot describe its actual life. Neither source states Aion's retirement date. For a **six-year illustrative assumption for Section VI**, continuous availability would deliver 189,345,600 node-seconds and the median 368-second run would claim `368 / 189,345,600 = 1.94e-6` of the node's lifetime, or 0.000194%. Actual uptime and retirement could change this share. |
| Runs per year | Student estimate given 2026-09-29 | **100 runs/year**, an explicit usage **assumption for Section VI**, not an observed III.B inventory value. At the 368-second baseline median, this would occupy 36,800 node-seconds (about 10.2 node-hours) per year. |

The local course file `S3-LCA-goal-and-scope.pdf`, slide 14, places sourced items in III.B and unsourced assumptions in Section VI. `S4-LCI-life-cycle-inventory.pdf`, slide 17, specifies the HW2 sections and deadline. The shared bibliography PDFs named in Session 4 were not present in the local course directory; the publisher and ULHPC sources linked above were read directly.

## Input facts, checked 2026-10-27

Run locally from the repository root on the input whose SHA-256 begins `dd2ef49aebabfed1` (the frozen input above). These back the read count in Section I and the lower-case check in Section III.A of the paper.

```
gzip -cd job/data/M_abscessus_HiSeq_10M.fa.gz |
  awk '/^>/{n++; next} /[acgtn]/{l++} END{print "records",n,"lowercase_lines",l+0}'
```

Output: `records 5000000 lowercase_lines 0`. `kc-py1.py` upper-cases only the last record, so a lower-case base elsewhere would be counted as a distinct 31-mer; with no lower-case sequence line in this input, that behaviour does not affect the histogram.

## HW4: AI-assisted optimisation and payback, 2026-10-27

All optimisation changes were made by OpenCode 1.19.3 with the pinned course model `openrouter/deepseek/deepseek-v4-flash-0731` (`opencode.json` unchanged). Agent files: `.opencode/agents/optimiser.md` and `builder.md` (model pinned, variant `low`, `steps: 30`, bash allow-list, no ssh/sbatch/git) plus `reader.md`; a five-line git-ignored `AGENTS.md` replaces the `CLAUDE.md` fallback, and every run used `OPENCODE_DISABLE_CLAUDE_CODE=1`, `--title` (avoids a title request to a different small model) and stdin closed (`</dev/null`; with stdin open, `opencode run` waited without creating a session and spent no tokens).

- Fixed cost of a one-word request (input tokens): 12,365 unconfigured (default agent, `CLAUDE.md` fallback); 5,920 with the optimiser agent; 4,786 with the reader agent.
- Sessions, exported with `opencode export --sanitize ID > opencode-ID.json`: two smoke tests, one optimiser diagnostic, optimiser task 1 (counter, 30 requests, step cap reached), task 2 (job script), task 3 (srun fix, resumed once for the memory margin), builder (tool, resumed once for the `--ntasks` fix), builder fix (Python 3.6). `python3 job/measurements/opencode-usage.py` sums them: 67 requests, 19,878 output + 18,180 reasoning tokens, 13.210 gCO2e at 1.03 Wh/1000 output tokens and 337 g/kWh.
- Author's checks: `kc-py1-opt.py` on the full input on the author's laptop (Python 3.14.4): SHA-256 `06a32de7…bf42`, 255.67 s, peak RSS 5,925,364 KB.
- Aion policy read 2026-10-27: `scontrol show partition batch` gives `MaxMemPerCPU=1750` (`CR_CORE_MEMORY`); `sinfo -p batch` showed 132 mixed nodes.
- Runs: `optimised-submissions-20261027.txt`. First submission (1 core, 8G) jobs 16118778/80/82 FAILED in 2–3 s with `srun: fatal: cpus-per-task set by two different environment variables SLURM_CPUS_PER_TASK=5 != SLURM_TRES_PER_TASK=cpu=1`; 16118784–87 cancelled before start. After the agent's fix (4 cores, 6800M, `run-optimised.sh` SHA-256 `ecd3ce65…5fb4`), jobs 16118792/94/96/98/800 COMPLETED on aion-0046 and aion-0037, all with the reference histogram hash; collectors copied `optimised-JOBID.txt`, `sacct-JOBID.txt`, `node-NODE.txt`.
- `python3 job/measurements/optimised-calculation.py 16118792 16118794 16118796 16118798 16118800` → `optimised-summary-20261027.txt`: 0.607 gCO2e per run (range 0.605–0.616), saving 14.281 g; the same chain on the baseline allocation gives 14.879 g (lcia: 14.888 g). Shared-node energy is attributed (idle share by cores held, program increment 5.217 W per busy core from the aion-0144 RAPL series, memory model on ReqMem), not measured.
- `python3 job/measurements/payback-calculation.py` → `payback-summary-20261027.txt`: cost 16.265 g (AI 13.210 g + Aion runs 3.054 g), payback 1.14 runs.
- Tool `job/tool/allocation-footprint.py`, run live on the Aion login node (Python 3.6.8): job 16118792 → 0.60 g; job 15861674 (idle measurement) → 2.45 g; job 16118778 → `error: job state is 'FAILED', not COMPLETED`, exit 1.

Wrong or rejected agent output (for Appendix B): (1) claimed the new counter's peak is "well under 1 GiB" — measured 5.65 GiB; (2) its first job script (1 core, 8G) failed on Aion because of `MaxMemPerCPU`; (3) estimated "~2–4 gCO2e per run" after optimisation — attributed 0.607 g; (4) called a 6 % memory margin (6G) "comfortable" — raised to 6800M on request; (5) the tool printed `--ntasks-per-node=N`, which would launch N copies — corrected; (6) the tool used `subprocess(text=True)`, unavailable on the Aion login node's Python 3.6 — corrected; (7) its README called the 913.7 kg figure a hardware mass — corrected.

### Related Work references, verified 2026-10-27

Each DOI was resolved through `https://doi.org/api/handles/DOI` (response code 1) and its metadata checked on Crossref; the full text was read in the course bibliography PDF (`/home/isaac/Downloads/biblio`) at the passage cited.

| Reference | DOI → landing page | Venue | Passage read |
| --- | --- | --- | --- |
| Wadenstein & Vanderbauwhede 2025 | 10.1140/epjc/s10052-025-14650-8 → link.springer.com | Eur. Phys. J. C 85(8):913 | Abstract; Section 6 Conclusions |
| Lakim et al. 2022 | 10.18653/v1/2022.bigscience-1.8 → aclanthology.org | Proc. BigScience Episode #5 Workshop, ACL, pp. 84–94 | Discussion (idle power, 4 % R&D experiments) |
| Avgerinou et al. 2017 | 10.3390/en10101470 → mdpi.com | Energies 10(10):1470 | Abstract (PUE declining yearly) |
| Elsworth et al. 2025 | 10.48550/arXiv.2508.15734 → arxiv.org (no Crossref record; preprint) | arXiv preprint, not peer reviewed | Abstract; "Idle Machine energy" in the methodology list; results paragraph with the 1.72 scaling |
| Oviedo et al. 2026 | 10.1016/j.joule.2026.102430 → Elsevier (403 to the fetcher) | Joule 10(8):102430 | Author version arXiv:2509.20241v2: abstract (0.31 Wh/query) and Fig. 2 caption (300 median output tokens) → 1.03 Wh/1000 output tokens |
| Lannelongue et al. 2021 | 10.1002/advs.202100707 → Wiley | Adv. Sci. 8(12):2100707 | Section 5 (already used in III.B) |

Checked 2026-10-28 after an external reference review:

- AR5 (Myhre et al. 2013), Chapter 8 PDF from ipcc.ch: note to Table 8.7, "These values do not include CO2 from methane oxidation. Values for fossil methane are higher by 1 and 2 for the 20 and 100 year metrics"; Table 8.A.1 lists fossil methane GWP100 = 30. III.C now compares fossil methane 30 → 29.8 (AR6), not 28 → 29.8.
- EU data-centre report: authors from the imprint page of `/home/isaac/Downloads/biblio/hpc/2025-EC-Energy-Performance-of-EU-Data-Centres.pdf` (Heatubun, Dragan, Bolchi, Lopes Bautista, Hinterholzer, Hintemann, Marx, Furda); PUE 1.36 is weighted by total energy consumption, n = 681.
- Oviedo et al., arXiv:2509.20241v2 (PDF): the standard query assumes 500 input tokens and 300 median output tokens; very long inputs raise prefill energy "substantially".
- Session 8 slides, slide 11: course factor 1.03 Wh per 1 000 output tokens, converted with "your grid factor (Section III.C)".
- OpenRouter models API (`https://openrouter.ai/api/v1/models`), read 2026-10-28: `deepseek/deepseek-v4-flash-0731` is "a sparse mixture-of-experts model from DeepSeek, with 13B active parameters out of 284B total". `opencode.json` routes it to novita, deepinfra or inceptron (no fallbacks); the session exports do not record which provider served a request.
- Avgerinou et al. 2017: the PUE trend covers reporting years 2009 to end of 2016.

## HW4 revision: optimise around the code only, 2026-11-10

Tutoring session, early November 2026: the optimisation may change only what surrounds the program (allocation, interpreter, compilation of the unchanged source), never `kc-py1.py` itself. The HW4 section above is therefore **superseded** for Sections IV–V: its counter rewrite is discarded.

- Rejected files moved to `job/optimised/rejected/` (README there): `kc-py1-opt.py` (SHA-256 `282b58df…68635`) and the `run-optimised.sh` that ran it (`ecd3ce65…5fb4`). `optimised-summary-20261027.txt` and `payback-summary-20261027.txt` describe that discarded path and are kept unchanged as records.
- `.opencode/agents/optimiser.md` rewritten: never edit, copy-and-modify or rewrite the program; allowed levers are the Slurm request and how the unchanged source runs; site facts (MaxMemPerCPU=1750, `lang/Cython/3.0.10-GCCcore-13.2.0` in release 2023b = `env/release/default` → `rhel810-20250803`, checked on the Aion login node 2026-11-10); `bash -n` added to the allow-list.
- OpenCode is now **2.2.0**; export is `opencode session export --sanitize ID` and the JSON format changed (flat messages with `type`). `opencode-usage.py` reads both formats; the eight 1.x exports still sum to 13.210 g.
- Sessions (optimiser agent, run with `opencode run --agent optimiser --format json --title … </dev/null`, `OPENCODE_DISABLE_CLAUDE_CODE=1`, started by Claude Code at the author's request):
  - `ses_e39d393d9ffexQ0DAMS0O5nJFq` right-sized script `job/optimised/run-rightsized.sh` (6 cores, 10G, 10 min, no `--exclusive`; 1.25 × 7.40 GiB → 10 GiB; 10240/1750 → 6 cores): 4 requests, 1,427 output tokens, 0.495 g.
  - `ses_e39d28e96ffe2cY33z7sMiWjMB` `build-cython.sh` + `run-cython.sh`: 15 requests, 7,307 output tokens, 2.536 g.
  - `ses_e39ce6350ffegS7XjYZprykhxy` build fix (`--module-name kc_py1`): 6 requests, 1,464 output tokens, 0.508 g.
- Smoke tests on a 100,000-read sample (`gzip -cd … | head -n 200000 | gzip` → `$SCRATCH/kmer-counting/sample-100k.fa.gz`, SHA-256 `ce17aa5a…2126`); frozen counter on the laptop: histogram `9d6e6f8f…2553`.
  - 16225100 build FAILED in 3 s: `'kc-py1' is not a valid module name` (`cython-build-16225100.txt`); 16225102 (Cython smoke) cancelled by the dependency before start.
  - 16225101 right-sized smoke, aion-0091, 8.01 s, histogram `9d6e6f8f…2553` (`smoke-16225101.txt`).
  - 16225112 build COMPLETED on aion-0089: Cython 3.0.10, GCC 13.2.0, Python 3.11.5; source `4628ab8d…0438` (frozen `kc-py1.py`), C `ea9d5015…6b`, executable `dae47ccb…4bc1`; one-read test `1<TAB>1` (`cython-build-16225112.txt`).
  - 16225113 Cython smoke, aion-0091, 7.46 s, histogram `9d6e6f8f…2553` (`smoke-16225113.txt`).
- Measured runs: `optimised-submissions-20261110.txt` (hashes of program, scripts, build, input; submitted 2026-11-10T16:04:02Z, alternating variants, `--dependency=singleton`, collector after each). Right-sized: 16225119, 123, 127, 131, 135. Cython: 16225121, 125, 129, 133, 137. All COMPLETED 0:0 with histogram `06a32de7…bf42`, MaxRSS 7.40 GiB; nodes aion-0167 (8 runs) and aion-0091 (2 runs), shared with other jobs.
- `python3 job/measurements/optimised-calculation.py 16225119 16225123 16225127 16225131 16225135` → `optimised-summary-rightsized-20261110.txt`: median Elapsed 367 s (362–377), 0.911 gCO2e per run (0.899–0.936). The model line of the 20261027 summary (frozen counter right-sized at baseline timing) predicted 0.904 g.
- `python3 job/measurements/optimised-calculation.py 16225121 16225125 16225129 16225133 16225137` → `optimised-summary-cython-20261110.txt`: median Elapsed 340 s (335–351), 0.844 gCO2e per run (0.832–0.872); saving 14.044 g.
- `python3 job/measurements/payback-calculation.py` (rewritten 2026-11-10: kept path only) → `payback-summary-20261110.txt`: AI 9.693 g (10 sessions, 62 requests, 27,924 output tokens; session `ses_e80fda1a…` excluded) + Aion 8.873 g (ten measured runs 8.812 g, seven short jobs from their sacct records 0.055 g, 13 collectors at 1 core/256 MB/2 s 0.006 g) = 18.566 g; payback 1.32 runs (4.8 days at 100/year). Sensitivities: discarded path 10.100 g (payback 2.04 runs if counted); AI ×10 → 7.53 runs; AI grid +100 g/kWh → +0.20 runs; freed cores idle → saving 6.51 g, payback 2.85 runs; Cython lever alone 7.302 g / 0.067 g per run → 109 runs (13 months).
- Tool check: `python3 job/tool/allocation-footprint.py --sacct job/measurements/sacct-16225119.txt` → 0.92 g, recommends 6 cores/10 GiB (saving 0.00); `--sacct …/sacct-16225121.txt` → 0.84 g, same recommendation.

Equal-node assumption (stated in III.A and VI): right-sized aion-0091 372 s vs aion-0167 median 366.5 s; Cython aion-0091 335 s vs aion-0167 median 341 s; spread on aion-0167 alone about 4 %. Earlier evidence: baseline aion-0127 368 s vs aion-0144 364 s; idle aion-0234 178.6 W vs aion-0144 182.6 W.

Wrong or rejected agent output (for Appendix B, items 8–10): (8) the first Cython build named the module after the file (`kc-py1`, invalid); (9) it described the `--embed` executable as having "no interpreter startup" — it embeds and starts CPython; (10) after the fix, it gave the histogram SHA-256 `06a32de…f42` as the expected source SHA-256 (the source is `4628ab8d…0438`).
