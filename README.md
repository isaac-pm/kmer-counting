# Carbon footprint of a k-mer counting job on an HPC node

A life cycle assessment of one HPC job, and of an AI-assisted optimisation of it, written as a short
paper for the Green IT 2026 course (University of Luxembourg, HPC track).

The job counts every canonical 31-mer in 5,000,000 DNA reads with `kc-py1.py`, a single-threaded
Python program from [lh3/kmer-cnt](https://github.com/lh3/kmer-cnt) (commit `e2574719`), on the Aion
cluster of the University of Luxembourg. The baseline holds a whole 128-core node for a program that
uses one core. The paper measures its footprint (15 gCO2e per run), optimises only what surrounds the
unchanged program (a right-sized request and a Cython build: 0.84 g per run), and computes the carbon
payback of that optimisation (1.32 runs).

## Where things are

```
pdf/short-paper-hpc.pdf          the paper
src/short-paper-hpc.tex          its LaTeX source; src/refs.bib the references
job/baseline/kc-py1.py           the frozen counter (never edited)
job/run-baseline.sh              the frozen baseline Slurm script (exclusive node)
job/run-baseline-energy.sh       the same run, bracketed by RAPL energy readings
job/optimised/                   the optimisation: run-rightsized.sh, build-cython.sh, run-cython.sh
job/optimised/rejected/          an earlier rewrite of the counter, kept as a record only
job/tool/                        allocation-footprint.py, the reusable tool, with its own README
job/measurements/                the evidence: logs, Slurm accounting records, calculation scripts,
                                 dated summaries, exported AI-agent sessions
job/measurements/README.md       the source register: commands, dates, job IDs, hashes, sources
.opencode/agents/                the AI coding agents used for the optimisation and the tool
opencode.json                    the pinned course model for those agents
```

## Reproduce

**The input.** It is not stored here. Download it and check its SHA-256:

```sh
mkdir -p job/data
curl -L -o job/data/M_abscessus_HiSeq_10M.fa.gz \
  https://github.com/lh3/kmer-cnt/releases/download/v0.1/M_abscessus_HiSeq_10M.fa.gz
sha256sum job/data/M_abscessus_HiSeq_10M.fa.gz
# dd2ef49aebabfed1574b55fd002025f29b2fda88c70b2095f5e1b3a822cee736
```

**The counter, locally** (Python 3, standard library only). The one-read test prints `1<TAB>1`; a
full run prints 255 lines with SHA-256 `06a32de7…bf42`:

```sh
printf '>read1\nACGTACGTACGTACGTACGTACGTACGTACG\n' | python3 job/baseline/kc-py1.py | awk '$2 != 0'
gzip -cd job/data/M_abscessus_HiSeq_10M.fa.gz | python3 job/baseline/kc-py1.py | sha256sum
```

**The runs, on Aion** (from the repository root on a login node; see `job/README.md`):

```sh
sbatch job/run-baseline.sh                  # baseline, exclusive node
sbatch job/optimised/run-rightsized.sh      # same program, 6 cores and 10G on a shared node
sbatch job/optimised/build-cython.sh        # once: compile the unchanged source with Cython
sbatch job/optimised/run-cython.sh          # the compiled program, same request
```

**The numbers, anywhere** (Python 3, standard library only; each prints to stdout and is compared
with its dated summary in `job/measurements/`):

```sh
python3 job/measurements/lcia-calculation.py              # baseline footprint, Section III
python3 job/measurements/optimised-calculation.py 16225121 16225125 16225129 16225133 16225137
python3 job/measurements/payback-calculation.py           # cost, saving and payback, Section V
```

**The tool, on any finished Slurm job:**

```sh
python3 job/tool/allocation-footprint.py --sacct job/measurements/sacct-16225121.txt
python3 job/tool/allocation-footprint.py --job JOBID      # on a cluster with sacct
```

## Building the paper

`latexmk` from the repository root builds every document in `src/` into `pdf/` (pdfLaTeX).

## License

MIT, see `LICENSE`.
