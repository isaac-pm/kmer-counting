#!/usr/bin/env python3
"""Allocation footprint for a finished Slurm job.

Shows what a job's allocation held vs what it used, the gCO2e per run of that
allocation (operational + embodied), and the right-sized request with its own
gCO2e.  Works offline from a saved ``sacct`` file or live by calling ``sacct``
for a job ID.
"""

import argparse
import math
import re
import subprocess
import sys

SACCT_FORMAT = (
    "JobID,JobName,NodeList,AllocNodes,AllocCPUS,ReqMem,MaxRSS,"
    "Elapsed,TotalCPU,State,ExitCode"
)


class JobError(Exception):
    """A clear, user-facing failure (missing field, job not finished, ...)."""


def parse_seconds(tok):
    """Parse a Slurm duration [D-]HH:MM:SS or MM:SS[.mmm] into seconds."""
    if not tok:
        return None
    tok = tok.strip()
    days = 0
    if "-" in tok:
        day_part, rest = tok.split("-", 1)
        try:
            days = int(day_part)
        except ValueError:
            raise JobError("bad duration field: %r" % tok)
    else:
        rest = tok
    parts = rest.split(":")
    try:
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h, m, s = 0, parts[0], parts[1]
        else:
            raise ValueError
        total = days * 86400 + int(h) * 3600 + int(m) * 60 + float(s)
    except ValueError:
        raise JobError("bad duration field: %r" % tok)
    return total


def parse_mem_gib(tok):
    """Parse a Slurm memory suffix (K/M/G/T, binary) into GiB."""
    if not tok:
        return None
    tok = tok.strip()
    m = re.match(r"([\d.]+)\s*([KMGTPE]?)$", tok, re.I)
    if not m:
        raise JobError("bad memory field: %r" % tok)
    num = float(m.group(1))
    unit = (m.group(2) or "K").upper()
    exp = {"K": 1, "M": 2, "G": 3, "T": 4, "P": 5, "E": 6}[unit]
    return num * (1024 ** exp) / (1024 ** 3)


def load_rows(source):
    """Return list of dict rows keyed by header, from text or live sacct."""
    if source.startswith("--job:"):
        job_id = source[len("--job:"):]
        cmd = ["sacct", "-j", job_id, "-P",
               "--format=" + SACCT_FORMAT]
        try:
            text = subprocess.check_output(cmd, universal_newlines=True)
        except subprocess.CalledProcessError as e:
            raise JobError("sacct failed for job %s: %s" % (job_id, e))
        except FileNotFoundError:
            raise JobError("sacct not found; use --sacct FILE offline")
    else:
        try:
            with open(source, "r") as fh:
                text = fh.read()
        except OSError as e:
            raise JobError("cannot read %s: %s" % (source, e))

    rows = []
    header = None
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if header is None:
            if line.startswith("JobID|"):
                header = line.split("|")
                continue
            else:
                # skip banners / command echoes before the header line
                continue
        fields = line.split("|")
        if len(fields) != len(header):
            # tolerant: ignore malformed rows, but keep if it's clearly a row
            continue
        rows.append(dict(zip(header, fields)))
    if header is None:
        raise JobError("no sacct table (no line starting with 'JobID|') in input")
    return rows


def pick_job_row(rows):
    """The job-level row (JobID without a step suffix) or None."""
    for r in rows:
        jid = (r.get("JobID") or "").strip()
        if jid and "." not in jid:
            return r
    return None


def get(row, name):
    val = (row.get(name) or "").strip()
    if not val:
        raise JobError("field %r missing on job row; cannot compute footprint"
                       % name)
    return val


def main():
    ap = argparse.ArgumentParser(
        description="Footprint of a finished Slurm allocation vs what it used.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sacct", metavar="FILE",
                     help="saved `sacct -P` output (skips lines before the "
                          "JobID| header)")
    src.add_argument("--job", metavar="ID",
                     help="run sacct live for this job ID")

    ap.add_argument("--node-cores", type=int, default=128,
                    help="installed cores per node (default 128)")
    ap.add_argument("--node-mem-gb", type=float, default=256,
                    help="installed memory per node, GiB (default 256)")
    ap.add_argument("--mem-per-core-mb", type=float, default=1750,
                    help="scheduler MaxMemPerCPU, MB/core (default 1750)")
    ap.add_argument("--idle-w", type=float, default=182.642,
                    help="node idle power, W (default 182.642)")
    ap.add_argument("--active-w", type=float, default=5.217,
                    help="marginal W per busy core (default 5.217)")
    ap.add_argument("--mem-w-per-gb", type=float, default=0.3725,
                    help="W per GiB of allocated memory (default 0.3725)")
    ap.add_argument("--pue", type=float, default=1.36,
                    help="power usage effectiveness (default 1.36)")
    ap.add_argument("--grid", type=float, default=337,
                    help="grid intensity, gCO2e/kWh (default 337)")
    ap.add_argument("--hardware-kg", type=float, default=913.7,
                    help="hardware mass per node, kg (default 913.7)")
    ap.add_argument("--life-years", type=float, default=6,
                    help="hardware lifetime, years (default 6)")
    args = ap.parse_args()

    source = "--job:" + args.job if args.job else args.sacct
    rows = load_rows(source)
    job = pick_job_row(rows)
    if job is None:
        raise JobError("no job-level row (JobID without a step suffix) found")

    # --- job-level fields (mandatory) ------------------------------------
    alloc_nodes = int(get(job, "AllocNodes"))
    alloc_cpus = int(get(job, "AllocCPUS"))
    req_mem = parse_mem_gib(get(job, "ReqMem"))
    elapsed = parse_seconds(get(job, "Elapsed"))
    total_cpu = parse_seconds(get(job, "TotalCPU"))
    state = get(job, "State")

    if state.strip().upper() != "COMPLETED":
        raise JobError("job state is %r, not COMPLETED" % state)
    if elapsed is None or elapsed <= 0:
        raise JobError("elapsed time missing/zero; cannot compute footprint")
    if total_cpu is None:
        raise JobError("TotalCPU missing; cannot compute footprint")
    if req_mem is None:
        raise JobError("ReqMem missing; cannot compute footprint")

    # MaxRSS: largest over all step rows (job row usually leaves it blank).
    max_rss = 0.0
    for r in rows:
        v = parse_mem_gib(r.get("MaxRSS") or "")
        if v is not None and v > max_rss:
            max_rss = v

    # --- per-node quantities ---------------------------------------------
    cores_per_node = alloc_cpus / alloc_nodes
    # If the whole node was allocated, count the entire installed memory;
    # otherwise fall back to the requested memory.
    if cores_per_node >= args.node_cores - 1e-9:
        mem_per_node = args.node_mem_gb
    else:
        mem_per_node = req_mem / alloc_nodes

    life_sec = args.life_years * 365.25 * 86400
    j_per_kwh = 3.6e6

    def footprint(cores_per_node, mem_gb_per_node, nodes):
        """Return (operational_g, embodied_g, energy_J) for one run."""
        cores = max(0, cores_per_node)
        mem = max(0, mem_gb_per_node)
        energy_j = (args.idle_w * cores / args.node_cores * elapsed
                    + args.active_w * total_cpu
                    + args.mem_w_per_gb * mem * elapsed)
        energy_j *= nodes
        operational = energy_j / j_per_kwh * args.pue * args.grid
        frac = max(cores / args.node_cores, mem / args.node_mem_gb)
        embodied = (args.hardware_kg * 1000 * frac * elapsed / life_sec) * nodes
        return operational, embodied, energy_j

    # --- what was held ---
    held_op, held_emb, held_j = footprint(cores_per_node, mem_per_node,
                                          alloc_nodes)
    held_g = held_op + held_emb

    # --- what was used ---
    cores_used = total_cpu / elapsed          # average busy cores
    used_mem = max_rss                        # GiB

    # --- right-sized request (same node count, same run time/CPU) --------
    right_cores = max(1, int(math.ceil(cores_used)))
    right_mem_gib = int(math.ceil(max_rss * 1.25))
    if right_mem_gib < 1:
        right_mem_gib = 1
    need_cores = int(math.ceil(right_mem_gib * 1024 / args.mem_per_core_mb))
    if need_cores > right_cores:
        right_cores = need_cores
    right_op, right_emb, right_j = footprint(right_cores, right_mem_gib,
                                             alloc_nodes)
    right_g = right_op + right_emb
    saving = held_g - right_g

    # --- report -----------------------------------------------------------
    def fmt_g(g):
        return "%.2f gCO2e" % g

    print("Allocation footprint  job %s  (%s)" % (job["JobID"], state))
    print("  held : %d nodes x %d cores, %.0f GiB requested, elapsed %ds, "
          "%.1f CPU-s" % (alloc_nodes, alloc_cpus, req_mem * alloc_nodes,
                          elapsed, total_cpu))
    print("  used : %.1f cores (TotalCPU/Elapsed), %.1f GiB MaxRSS"
          % (cores_used, used_mem))
    print("held footprint:   %s  (operational %.2f + embodied %.2f)"
          % (fmt_g(held_g), held_op, held_emb))
    print("right-sized:      %d cores, %d GiB  ->  %s  (operational %.2f + "
          "embodied %.2f)" % (right_cores, right_mem_gib, fmt_g(right_g),
                              right_op, right_emb))
    print("saving:           %s" % fmt_g(saving))
    print("#SBATCH --nodes=%d" % alloc_nodes)
    print("#SBATCH --ntasks=1")
    print("#SBATCH --cpus-per-task=%d" % right_cores)
    print("#SBATCH --mem=%dG" % right_mem_gib)


if __name__ == "__main__":
    try:
        main()
    except JobError as e:
        sys.stderr.write("error: %s\n" % e)
        sys.exit(1)
