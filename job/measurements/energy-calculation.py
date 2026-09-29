#!/usr/bin/env python3
"""Recompute the five Aion CPU-package readings and idle subtraction."""

from datetime import datetime, timezone
from pathlib import Path
from statistics import median
import re


ROOT = Path(__file__).resolve().parent
IDS = (15861652, 15861654, 15861656, 15861658, 15861660)
EXPECTED_HASH = "06a32de77200121a397050e015a257953dc956b7854027a1ed73b15afc12bf42"


def extract(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    if match is None:
        raise ValueError(f"Missing pattern: {pattern}")
    return match.group(1)


idle_text = (ROOT / "idle-15861674.txt").read_text()
idle_joules = int(extract(r"RAPL CPU package total: (\d+) uJ", idle_text)) / 1_000_000
idle_seconds = float(extract(r"([\d.]+) seconds time elapsed", idle_text))
idle_watts = idle_joules / idle_seconds

print(f"UTC calculation: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
print("$ python3 job/measurements/energy-calculation.py")
print("Source: job/measurements/baseline-JOBID.txt (RAPL total, perf elapsed, SHA-256)")
print("Source: job/measurements/sacct-JOBID.txt (State, ExitCode, NodeList, Elapsed)")
print("Source: job/measurements/idle-15861674.txt (RAPL total, perf elapsed)")
print(f"Idle: {idle_joules:.6f} J / {idle_seconds:.9f} s = {idle_watts:.6f} W")
print("JOBID|Slurm elapsed|perf elapsed s|package J|idle-subtracted package J|output SHA-256")

gross = []
net = []
for job_id in IDS:
    log = (ROOT / f"baseline-{job_id}.txt").read_text()
    accounting = (ROOT / f"sacct-{job_id}.txt").read_text()
    joules = int(extract(r"RAPL CPU package total: (\d+) uJ", log)) / 1_000_000
    seconds = float(extract(r"([\d.]+) seconds time elapsed", log))
    output_hash = extract(r"([a-f0-9]{64})  job/results/baseline-\d+\.tsv", log)
    if output_hash != EXPECTED_HASH:
        raise ValueError(f"Unexpected output hash for {job_id}")
    row = next(line.split("|") for line in accounting.splitlines() if line.startswith(f"{job_id}|"))
    if row[4] != "aion-0144" or row[-2:] != ["COMPLETED", "0:0"]:
        raise ValueError(f"Unexpected accounting state for {job_id}: {row}")
    elapsed = row[9]
    incremental = joules - idle_watts * seconds
    gross.append(joules)
    net.append(incremental)
    print(f"{job_id}|{elapsed}|{seconds:.9f}|{joules:.6f}|{incremental:.6f}|{output_hash}")

print(f"Median package energy: {median(gross):.6f} J")
print(f"Median idle-subtracted package energy: {median(net):.6f} J")
print("Idle subtraction assumes the subsequent 60-second idle rate applies during each run.")
print("RAPL measures CPU packages, not whole-node or facility electricity.")
