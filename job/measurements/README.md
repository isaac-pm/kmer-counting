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

Slurm recorded `AllocNodes=1`, `AllocCPUS=128`, and `ReqMem=224000M` for every baseline. The Python-step peak RSS is about 7.4 GiB if Slurm's `K` denotes KiB, roughly 3.5% of the reservable memory; these are different quantities. The node record shows `CPUTot=128`, `Sockets=8` (Slurm's virtual sockets), `RealMemory=224000`, and `CurrentWatts=n/a` and `AveWatts=n/a`. ULHPC's specification separately lists two physical sockets and 256 GB installed RAM.

Every `ConsumedEnergy` and `ConsumedEnergyRaw` cell in all five `sacct` records, for the job and its `.batch`, `.extern`, and `.0` steps, is **empty**, observed 2026-09-29. This is missing telemetry, not zero joules. The disk counters are accounting estimates at step level; do not add the batch and Python numbers or identify them with exact GPFS bytes, because the gzip-to-Python pipe and accounting scope can overlap.

For a transparent energy substitute, Lannelongue's Section 5 formula can be evaluated with the 368-second median, the documented 280 W CPU TDP / 64 cores, 256 GB installed memory, its 0.3725 W/GB memory coefficient, and the declared PUE 1.36. Counting one active core gives **0.014 kWh of modelled site electricity**; applying full TDP to all 128 allocated cores gives **0.091 kWh**. These are sensitivity scenarios, not measurements or guaranteed bounds: the first omits idle CPU, board, storage and fabric power, while the second treats all cores as fully active despite the serial Python code. A defensible central node-energy estimate requires an idle-power source or working node energy telemetry.

## How to read the accounting

- `Elapsed`, `AllocNodes`, `AllocCPUS`, and `NodeList` describe the allocated resource and occupancy. `ReqMem` is Slurm's reservable memory, not necessarily the node's physical RAM. A live accounting row for the first job reported `224000M`; the Aion hardware page specifies 256 GB physically.
- Read `MaxRSS` on the Python step (`JOBID.0`) and compare it with `Maximum resident set size` in `baseline-JOBID.txt`. `MaxRSS` is a peak, not total memory allocated.
- Check both `JOBID.batch` and `JOBID.0` for `MaxDiskRead` and `MaxDiskWrite`: `gzip` runs in the batch shell and Python reads a pipe. These counters may not represent all file system traffic or page-cache hits.
- Inspect `ConsumedEnergy` and `ConsumedEnergyRaw` on every step, including blanks or zeros. Neither is an energy measurement until a nonzero counter with defined units is established.
- Verify `State` and `ExitCode` for all runs. Compare TSV hashes and all five elapsed times; report the median and range once complete.

## Source register for III.B and later calculations

| Quantity | Source read 2026-09-29 | Evidence and limits |
| --- | --- | --- |
| Aion node | [ULHPC Aion compute nodes](https://hpc-docs.uni.lu/systems/aion/compute/) | Two physical AMD EPYC 7H12 sockets, 64 cores and 280 W TDP per CPU; 128 cores and 256 GB DDR4 3200 memory per node. Slurm exposes eight virtual sockets. Aion uses BullSequana X2410 blades, HDR100 InfiniBand, and a 480 GB local SSD. TDP is not measured energy. |
| Shared storage and interconnect | [ULHPC Aion overview](https://hpc-docs.uni.lu/systems/aion/), [interconnect](https://hpc-docs.uni.lu/systems/aion/interconnect/), [GPFS](https://hpc-docs.uni.lu/filesystems/gpfs/) | Home is on shared GPFS/SpectrumScale; Aion has a 12 switch HDR100 fabric. This job has one compute node, so no node-to-node application communication is claimed; storage I/O still crosses the fabric. Component energy and embodied shares are not available from these pages. |
| Site PUE proxy | [European Commission, *Assessment of the Energy Performance and Sustainability of Data Centres in the EU*, first technical report (2025), p. 34](https://data.europa.eu/doi/10.2833/3168794) | EU reported 2024 average PUE **1.36**. This can be *declared as a regional proxy*, since Session 3 says the centre publishes no Aion PUE. It is not a measurement of the University of Luxembourg site. |
| Energy substitute, if Slurm has no usable value | [Lannelongue et al., *Green Algorithms* (2021), Section 5, Experimental Section](https://doi.org/10.1002/advs.202100707) | Equation (1): `E[kWh] = t[h] * (n_c * P_c[W] * u_c + n_m[GB] * P_m[W]) * PUE / 1000`. Paper gives 0.3725 W/GB for memory and discusses TDP as a processor power proxy. Its model omits motherboard, storage, and idle power of cores excluded through `u_c`; care is needed for an exclusive 128 core allocation running one Python process. |
| Server embodied-impact candidate | [Dell, *Full LCA of PowerEdge R6515/R7515/R6525/R7525*, Table 4-5](https://www.delltechnologies.com/asset/en-us/products/servers/technical-support/full-lca-of-dell-severs-r6515-r7515-r6525-r7525.pdf) and [R7525 specification](https://i.dell.com/sites/csdocuments/Product_Docs/en/PowerEdge-R7525-Spec-Sheet.pdf) | Dell reports **1,768.4 kg CO2e** for production of the assessed two-socket AMD EPYC R7525, including **854.7 kg** for its two 4 TB SSDs. Aion has one 480 GB local SSD and uses a liquid-cooled three-node blade. **Do not use 1,768.4 kg as Aion's measured footprint:** the Dell LCA uses IPCC 2013 GWP100 rather than the course's IPCC 2021 convention, and its hardware differs. It is a documented proxy candidate for later sensitivity analysis, pending selection of a compatible factor. |
| ecoQuery search | [ecoinvent 3.11 cut-off search for `server production`](https://ecoquery.ecoinvent.org/3.11/cutoff/search?query=server+production&currentPage=1&pageSize=10&searchBy=activity) | Ten activity matches were displayed on 2026-09-29, including desktop/laptop computer and internet access equipment production, but no server production activity. This is evidence of this search, **not proof that the database contains no usable component dataset**. Full impact scores require sign-in. |
| Service life | [ULHPC Aion timeline](https://hpc-docs.uni.lu/systems/aion/timeline/) and [Dell R7525 PCF](https://www.delltechnologies.com/asset/en-us/products/servers/briefs-summaries/poweredge-r7525-pcf-report.pdf) | Aion entered production in October–November 2021 and is still operating in September 2026, so Dell's four-year modelling lifetime for a different server cannot describe its actual life. Neither source states Aion's retirement date. For a **six-year illustrative assumption for Section VI**, continuous availability would deliver 189,345,600 node-seconds and the median 368-second run would claim `368 / 189,345,600 = 1.94e-6` of the node's lifetime, or 0.000194%. Actual uptime and retirement could change this share. |
| Runs per year | No observed workload count yet | Treat any scenario as an **assumption for Section VI**, not an observed III.B inventory value. |

The local course file `S3-LCA-goal-and-scope.pdf`, slide 14, places sourced items in III.B and unsourced assumptions in Section VI. `S4-LCI-life-cycle-inventory.pdf`, slide 17, specifies the HW2 sections and deadline. The shared bibliography PDFs named in Session 4 were not present in the local course directory; the publisher and ULHPC sources linked above were read directly.
