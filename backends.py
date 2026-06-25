"""
backends.py  --  one place to choose WHO solves the QUBO.

The whole point of the QUBO formulation is that the *problem* (the qubo dict) is
fixed, and we can swap the *solver* freely. This module is that swap point.

Supported backends
-------------------
  neal   : classical simulated annealing on your laptop (default, free, offline)
  dwave  : a REAL D-Wave quantum annealer via Leap (free tier, needs a token)
  tabu   : classical Tabu search (another classical baseline, offline)

All of them consume the IDENTICAL qubo dict produced by build_route_qubo /
build_speed_qubo. That is the headline: same formulation, different hardware.

Getting a free D-Wave token (for backend="dwave")
-------------------------------------------------
  1. Sign up at  https://cloud.dwavesys.com/leap/signup/   (free)
  2. Copy your API token from the dashboard (Leap > top-right, "API Token").
  3. Run once:   dwave config create        (paste the token when prompted)
     or set:     setx DWAVE_API_TOKEN "DEV-xxxxxxxx...."   (then reopen shell)
  The free tier gives ~1 minute of QPU time per month -- our grids use only
  microseconds per solve, so that is plenty.
"""

from __future__ import annotations


def make_sampler(backend: str):
    """Return (sampler, label, is_quantum) for the requested backend."""
    backend = backend.lower()

    if backend == "neal":
        import neal
        return neal.SimulatedAnnealingSampler(), "neal (classical simulated annealing)", False

    if backend == "dwave":
        # Real quantum annealer. EmbeddingComposite maps our logical QUBO onto
        # the QPU's physical qubit graph automatically (minor-embedding).
        from dwave.system import DWaveSampler, EmbeddingComposite
        qpu = DWaveSampler()                      # picks an available QPU solver
        sampler = EmbeddingComposite(qpu)
        name = getattr(qpu, "solver", None)
        name = getattr(name, "id", "unknown") if name else "unknown"
        return sampler, f"D-Wave QPU  [{name}]  (REAL quantum annealer)", True

    if backend == "tabu":
        from dwave.samplers import TabuSampler
        return TabuSampler(), "Tabu search (classical metaheuristic)", False

    raise ValueError(f"Unknown backend '{backend}'. "
                     f"Choose from: neal, dwave, tabu.")


def sample_qubo(sampler, backend: str, qubo, num_reads: int,
                sweeps: int = 1000, seed: int = 42):
    """Solve the QUBO, passing only the kwargs each backend understands.

    neal  accepts num_sweeps + seed (it is software, fully reproducible).
    dwave accepts neither -- a physical QPU has no 'sweeps' and no RNG seed;
          its knobs are num_reads (how many anneals) + annealing_time.
    tabu  accepts num_reads only.
    """
    backend = backend.lower()

    if backend == "neal":
        return sampler.sample_qubo(qubo, num_reads=num_reads,
                                   num_sweeps=sweeps, seed=seed)
    if backend == "dwave":
        return sampler.sample_qubo(qubo, num_reads=num_reads)
    if backend == "tabu":
        return sampler.sample_qubo(qubo, num_reads=num_reads)

    raise ValueError(f"Unknown backend '{backend}'.")


def describe_run(sampleset, backend: str) -> str:
    """A short human-readable note about HOW the solve went (timing, chains)."""
    backend = backend.lower()
    info = getattr(sampleset, "info", {}) or {}

    if backend == "dwave":
        lines = []
        timing = info.get("timing", {})
        qpu_us = timing.get("qpu_access_time")
        if qpu_us is not None:
            lines.append(f"QPU access time: {qpu_us/1000:.2f} ms "
                         f"({qpu_us} microseconds)")
        # Embedding context: how many physical qubits each logical var used.
        emb = info.get("embedding_context", {}).get("embedding")
        if emb:
            chain_lens = [len(v) for v in emb.values()]
            phys = sum(chain_lens)
            lines.append(f"Minor-embedding: {len(emb)} logical vars -> "
                         f"{phys} physical qubits "
                         f"(max chain length {max(chain_lens)})")
        return "\n".join("    " + ln for ln in lines) if lines else \
            "    (no QPU timing returned)"

    return ""
