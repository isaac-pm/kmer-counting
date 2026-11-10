#!/usr/bin/env python3
"""gCO2e per run of the optimised job on a shared allocation (Section IV.C), on the baseline chain.

RAPL cannot be attributed on a shared node, so each run is charged its share of the node:
  idle package rate x cores held / 128 x Elapsed     (the idle draw the allocation reserves)
+ program increment per CPU-second x TotalCPU         (the program's own work, from the RAPL series)
+ memory coefficient x reserved GB x Elapsed          (Green Algorithms, as in the baseline)
then x PUE x grid, plus production x max(core share, memory share) x Elapsed / service life.
With 128 cores and 256 GB this reproduces the baseline chain of lcia-calculation.py.

Usage: python3 job/measurements/optimised-calculation.py JOBID [JOBID ...]
"""

from datetime import datetime, timezone
from pathlib import Path
from statistics import median
import re
import sys


ROOT = Path(__file__).resolve().parent
BASELINE_IDS = (15861652, 15861654, 15861656, 15861658, 15861660)  # aion-0144 RAPL series
EXPECTED_HASH = "06a32de77200121a397050e015a257953dc956b7854027a1ed73b15afc12bf42"

# Same factors as lcia-calculation.py, each with its source (see README.md, source register).
GRID_G_PER_KWH = 337.0
PUE = 1.36
MEMORY_W_PER_GB = 0.3725
NODE_MEMORY_GB = 256
NODE_CORES = 128
HARDWARE_G = 913_700.0           # Dell R7525 without its two 4 TB SSDs
SERVICE_LIFE_S = 6 * 365.25 * 24 * 3600


def extract(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"Missing pattern: {pattern}")
    return match.group(1)


def seconds(value: str) -> float:
    """Slurm durations: [D-]HH:MM:SS, MM:SS.mmm or HH:MM:SS.mmm."""
    days = 0
    if "-" in value:
        day_text, value = value.split("-")
        days = int(day_text)
    parts = [float(part) for part in value.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def mebibytes(value: str) -> float:
    units = {"K": 1 / 1024, "M": 1.0, "G": 1024.0, "T": 1024.0 ** 2}
    return float(value[:-1]) * units[value[-1]]


def rows(job_id: int) -> dict:
    lines = (ROOT / f"sacct-{job_id}.txt").read_text().splitlines()
    header = lines[0].split("|")
    return {line.split("|")[0]: dict(zip(header, line.split("|"))) for line in lines[1:]}


def run(job_id: int) -> dict:
    record = rows(job_id)
    job, step = record[str(job_id)], record[f"{job_id}.0"]
    if job["State"] != "COMPLETED" or job["ExitCode"] != "0:0":
        raise ValueError(f"{job_id}: {job['State']} {job['ExitCode']}")
    return {"id": job_id, "node": job["NodeList"], "cores": int(job["AllocCPUS"]),
            "mem_gb": mebibytes(job["ReqMem"]) * 1.048576 / 1000,
            "elapsed": seconds(job["Elapsed"]), "cpu": seconds(step["TotalCPU"]),
            "maxrss_gib": mebibytes(step["MaxRSS"]) / 1024}


def footprint(cores: int, mem_gb: float, elapsed: float, cpu: float, idle_w: float, active_w: float) -> dict:
    idle_j = idle_w * cores / NODE_CORES * elapsed
    active_j = active_w * cpu
    memory_j = MEMORY_W_PER_GB * mem_gb * elapsed
    node_j = idle_j + active_j + memory_j
    operational = node_j / 3.6e6 * PUE * GRID_G_PER_KWH
    share = max(cores / NODE_CORES, mem_gb / NODE_MEMORY_GB)
    embodied = HARDWARE_G * share * elapsed / SERVICE_LIFE_S
    return {"idle_j": idle_j, "active_j": active_j, "memory_j": memory_j, "node_j": node_j,
            "operational": operational, "embodied": embodied, "total": operational + embodied}


idle_text = (ROOT / "idle-15861674.txt").read_text()
idle_watts = (int(extract(r"RAPL CPU package total: (\d+) uJ", idle_text)) / 1e6
              / float(extract(r"([\d.]+) seconds time elapsed", idle_text)))

# Program increment per CPU-second, from the five baseline RAPL runs on aion-0144.
increments = []
for job_id in BASELINE_IDS:
    log = (ROOT / f"baseline-{job_id}.txt").read_text()
    package = int(extract(r"RAPL CPU package total: (\d+) uJ", log)) / 1e6
    step_s = float(extract(r"([\d.]+) seconds time elapsed", log))
    increments.append((package - idle_watts * step_s) / run(job_id)["cpu"])
active_watts = median(increments)

print(f"UTC calculation: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
print("$ python3 job/measurements/optimised-calculation.py " + " ".join(sys.argv[1:]))
print(f"Idle packages {idle_watts:.3f} W ({idle_watts / NODE_CORES:.3f} W per core held) | "
      f"program increment {active_watts:.3f} W per busy core (median of {len(increments)} RAPL runs)")
print(f"Grid {GRID_G_PER_KWH} gCO2e/kWh | PUE {PUE} | memory {MEMORY_W_PER_GB} W/GB | "
      f"hardware {HARDWARE_G / 1000} kg over {SERVICE_LIFE_S:.0f} s")

base = [run(job_id) for job_id in BASELINE_IDS]
check = footprint(NODE_CORES, NODE_MEMORY_GB, median(r["elapsed"] for r in base),
                  median(r["cpu"] for r in base), idle_watts, active_watts)
print(f"Check, baseline allocation (128 cores, 256 GB, median aion-0144 run): "
      f"{check['node_j']:.0f} J, {check['total']:.3f} gCO2e (lcia-calculation.py: 103146 J, 14.888 g)")

if len(sys.argv) > 1:
    runs = [run(int(arg)) for arg in sys.argv[1:]]
    for r in runs:
        log = (ROOT / f"optimised-{r['id']}.txt").read_text()
        if EXPECTED_HASH not in log:
            raise ValueError(f"{r['id']}: histogram hash not found in the log")
    print("\nJOBID|node|cores|reserved GB|Elapsed s|TotalCPU s|MaxRSS GiB|node J|gCO2e")
    results = []
    for r in runs:
        f = footprint(r["cores"], r["mem_gb"], r["elapsed"], r["cpu"], idle_watts, active_watts)
        results.append(f)
        print(f"{r['id']}|{r['node']}|{r['cores']}|{r['mem_gb']:.2f}|{r['elapsed']:.0f}|{r['cpu']:.1f}|"
              f"{r['maxrss_gib']:.2f}|{f['node_j']:.0f}|{f['total']:.3f}")
    med = {key: median(f[key] for f in results) for key in results[0]}
    print(f"Median Elapsed {median(r['elapsed'] for r in runs):.0f} s "
          f"(range {min(r['elapsed'] for r in runs):.0f}-{max(r['elapsed'] for r in runs):.0f}); "
          f"median TotalCPU {median(r['cpu'] for r in runs):.1f} s; "
          f"median MaxRSS {median(r['maxrss_gib'] for r in runs):.2f} GiB")
    print(f"Median parts: idle share {med['idle_j']:.0f} J | program {med['active_j']:.0f} J | "
          f"memory {med['memory_j']:.0f} J | node {med['node_j']:.0f} J")
    print(f"Median operational {med['operational']:.3f} g + embodied {med['embodied']:.4f} g = "
          f"{med['total']:.3f} gCO2e per run (range {min(f['total'] for f in results):.3f}-"
          f"{max(f['total'] for f in results):.3f})")
    print(f"Saving per run against the baseline 14.888 g: {14.888 - med['total']:.3f} gCO2e")
    # Split of the saving: the frozen counter cannot fit in the new request (7.4 GiB peak), so it is
    # charged the request the IV.D rule gives it, 10 GiB (peak x 1.25) and 6 cores (MaxMemPerCPU 1750 MB),
    # timed as in the baseline series.
    alloc_only = footprint(6, 10 * 1.073741824, median(r["elapsed"] for r in base),
                           median(r["cpu"] for r in base), idle_watts, active_watts)
    print(f"Model, frozen counter right-sized (6 cores, 10 GiB) at baseline timing: {alloc_only['total']:.3f} gCO2e")
print("Shared-node energy is attributed, not measured; Section VI names the limits.")
