#!/usr/bin/env python3
"""Turn the aion-0144 energy series into gCO2e per run (Section III.C) and its scenarios (III.D)."""

from datetime import datetime, timezone
from pathlib import Path
from statistics import median
import re


ROOT = Path(__file__).resolve().parent
IDS = (15861652, 15861654, 15861656, 15861658, 15861660)
BASELINE_IDS = (15860349, 15860350, 15860351, 15860352, 15860353)
EXPECTED_HASH = "06a32de77200121a397050e015a257953dc956b7854027a1ed73b15afc12bf42"

# Factors, each with its source (see README.md, source register).
GRID_G_PER_KWH = 337.0        # ecoinvent 3.11 cut-off, market for electricity, low voltage, LU, IPCC 2021 GWP100, read 2026-10-19
PUE = 1.36                    # EU average 2023 data, European Commission (2025), Figure 6
MEMORY_W_PER_GB = 0.3725      # Lannelongue et al. (2021), Section 5
MEMORY_GB = 256               # installed per Aion node, ULHPC compute page
TDP_W_PER_CORE = 280 / 64     # AMD EPYC 7H12 TDP per core, ULHPC compute page
CORES = 128
DELL_TOTAL_KG = 1768.4        # Dell R7525 production, Sphera (2021) Table 4-5, IPCC 2013 GWP100
DELL_SSD_KG = 854.7           # of which the two 4 TB SSDs
ECOINVENT_DESKTOP_KG = 221.0  # ecoinvent 3.11 desktop without screen, IPCC 2021 GWP100
SERVICE_LIFE_S = 6 * 365.25 * 24 * 3600  # six-year assumption = 189,345,600 s


def extract(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"Missing pattern: {pattern}")
    return match.group(1)


def seconds(hms: str) -> int:
    h, m, s = (int(part) for part in hms.split(":"))
    return 3600 * h + 60 * m + s


def job_row(job_id: int, node: str) -> list[str]:
    text = (ROOT / f"sacct-{job_id}.txt").read_text()
    row = next(line.split("|") for line in text.splitlines() if line.startswith(f"{job_id}|"))
    if row[4] != node or row[-2:] != ["COMPLETED", "0:0"]:
        raise ValueError(f"Unexpected accounting state for {job_id}: {row}")
    return row


def kwh(joules: float) -> float:
    return joules / 3.6e6


idle_text = (ROOT / "idle-15861674.txt").read_text()
idle_watts = (int(extract(r"RAPL CPU package total: (\d+) uJ", idle_text)) / 1e6
              / float(extract(r"([\d.]+) seconds time elapsed", idle_text)))
memory_watts = MEMORY_W_PER_GB * MEMORY_GB

print(f"UTC calculation: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
print("$ python3 job/measurements/lcia-calculation.py")
print("Source: baseline-JOBID.txt, sacct-JOBID.txt, idle-15861674.txt (aion-0144 series)")
print(f"Grid {GRID_G_PER_KWH} gCO2e/kWh | PUE {PUE} | memory {memory_watts:.2f} W | idle packages {idle_watts:.3f} W")
print("JOBID|Slurm elapsed s|perf s|package J|package over allocation J|node estimate J (packages + memory)")

rows = []
for job_id in IDS:
    log = (ROOT / f"baseline-{job_id}.txt").read_text()
    if extract(r"([a-f0-9]{64})  job/results/baseline-\d+\.tsv", log) != EXPECTED_HASH:
        raise ValueError(f"Unexpected output hash for {job_id}")
    package = int(extract(r"RAPL CPU package total: (\d+) uJ", log)) / 1e6
    step = float(extract(r"([\d.]+) seconds time elapsed", log))
    elapsed = seconds(job_row(job_id, "aion-0144")[9])
    # Outside the Python step the node is assumed to draw the idle package rate.
    package_alloc = package + idle_watts * (elapsed - step)
    node = package_alloc + memory_watts * elapsed
    rows.append((elapsed, step, package, package_alloc, node))
    print(f"{job_id}|{elapsed}|{step:.3f}|{package:.1f}|{package_alloc:.1f}|{node:.1f}")

elapsed_med = median(r[0] for r in rows)
step_med = median(r[1] for r in rows)
package_med = median(r[2] for r in rows)
package_alloc_med = median(r[3] for r in rows)
node_med = median(r[4] for r in rows)
active_med = median(r[2] - idle_watts * r[1] for r in rows)
aion0127_med = median(seconds(job_row(j, "aion-0127")[9]) for j in BASELINE_IDS)
print(f"Median Slurm elapsed aion-0144: {elapsed_med} s (aion-0127 series: {aion0127_med} s)")
print(f"Median perf step: {step_med:.3f} s")

share = elapsed_med / SERVICE_LIFE_S
embodied = {
    "Dell R7525 without its two 4 TB SSDs (chosen)": (DELL_TOTAL_KG - DELL_SSD_KG) * 1000 * share,
    "ecoinvent desktop without screen (low)": ECOINVENT_DESKTOP_KG * 1000 * share,
    "Dell R7525 as published (high)": DELL_TOTAL_KG * 1000 * share,
}
print(f"Lifetime share: {elapsed_med} / {SERVICE_LIFE_S:.0f} = {share:.4e}")
for name, grams in embodied.items():
    print(f"Embodied, {name}: {grams:.3f} gCO2e")
chosen_embodied = next(iter(embodied.values()))

print()
print("Scenario|IT energy J|IT kWh|site kWh (x PUE)|operational gCO2e|total with chosen embodied gCO2e")
scenarios = {
    "Packages, Python step only (HW2 carried value)": package_med,
    "Packages above idle, Python step": active_med,
    "Chosen: packages over allocation + memory model": node_med,
    "Green Algorithms, 1 core + 256 GB": (TDP_W_PER_CORE + memory_watts) * elapsed_med,
    "Green Algorithms, 128 cores at TDP + 256 GB": (CORES * TDP_W_PER_CORE + memory_watts) * elapsed_med,
}
for name, joules in scenarios.items():
    site = kwh(joules) * PUE
    operational = site * GRID_G_PER_KWH
    print(f"{name}|{joules:.0f}|{kwh(joules):.5f}|{site:.5f}|{operational:.3f}|{operational + chosen_embodied:.3f}")

print()
operational = kwh(node_med) * PUE * GRID_G_PER_KWH
total = operational + chosen_embodied
idle_part = package_alloc_med - active_med
parts = {
    "CPU packages at idle rate": idle_part,
    "CPU packages above idle": active_med,
    "Memory (model)": memory_watts * elapsed_med,
}
print(f"Chosen result: {operational:.3f} operational + {chosen_embodied:.3f} embodied = {total:.3f} gCO2e per run")
print("Share of total gCO2e per run, each energy part with its PUE overhead|gCO2e|share")
it_joules = sum(parts.values())
for name, joules in parts.items():
    grams = kwh(joules) * PUE * GRID_G_PER_KWH
    print(f"{name}|{grams:.3f}|{grams / total:.1%}")
print(f"Embodied, chosen|{chosen_embodied:.3f}|{chosen_embodied / total:.1%}")
overhead = kwh(node_med) * (PUE - 1) * GRID_G_PER_KWH
print(f"Of the total, site overhead (PUE - 1) alone: {overhead:.3f} gCO2e, {overhead / total:.1%}")
print(f"Check: IT sum {it_joules:.1f} J vs node median {node_med:.1f} J (medians of parts need not add exactly)")

print()
print("Sensitivity of the chosen total (one input moved, all else fixed)|gCO2e per run")
for pue in (1.1, 1.2, 1.5, 1.6):
    print(f"PUE {pue}|{kwh(node_med) * pue * GRID_G_PER_KWH + chosen_embodied:.3f}")
for years in (4, 8):
    life_share = elapsed_med / (years * 365.25 * 24 * 3600)
    print(f"Service life {years} years|{operational + (DELL_TOTAL_KG - DELL_SSD_KG) * 1000 * life_share:.3f}")
for watts in (50, 100):
    extra = kwh(watts * elapsed_med) * PUE * GRID_G_PER_KWH
    print(f"Unmeasured node components at {watts} W|{total + extra:.3f} (+{extra:.3f})")
print(f"Walltime of aion-0127 ({aion0127_med} s) instead of aion-0144|{total * aion0127_med / elapsed_med:.3f}")

print()
print("Comparators, chosen total")
led = 5 / 1000 * GRID_G_PER_KWH
print(f"5 W LED for one hour on the same grid: {led:.3f} gCO2e, so one run = {total / led:.1f} h")
print(f"Small petrol car, 291 gCO2e/km: one run = {total / 291 * 1000:.0f} m")
print(f"100 runs per year: {total * 100 / 1000:.2f} kgCO2e")
print("Package energy is measured (RAPL); memory power is modelled; board, fans, SSD and NIC are not counted.")
