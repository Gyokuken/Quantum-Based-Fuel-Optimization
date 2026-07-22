"""
quantum_qaoa.py -- run the fleet ASSIGNMENT QUBO on a REAL quantum optimizer (QAOA).

This is the step that turns "quantum-ready" into "quantum-running". The outer
assignment problem is already a QUBO (hybrid.build_assignment_qubo); here we solve
it with QAOA -- a genuine quantum optimization algorithm -- instead of the classical
neal stand-in. The candidate assignments QAOA returns are then scored EXACTLY by the
same classical oracle, exactly like the neal hybrid. Only the outer solver changes.

BACKENDS (swap with one argument)
---------------------------------
  "aer" : local Aer statevector SIMULATOR of a quantum computer. Works now, no
          account. Good for developing/verifying the pipeline; NOT real hardware.
  "ibm" : a REAL IBM quantum processor via Qiskit Runtime. Needs a free IBM
          Quantum account + API token (see below). Same QAOA, real qubits.

GET A FREE IBM QUANTUM TOKEN (for backend="ibm")
------------------------------------------------
  1. Sign up (free): https://quantum.ibm.com/
  2. Copy your API token from the dashboard.
  3. Save it once:
        from qiskit_ibm_runtime import QiskitRuntimeService
        QiskitRuntimeService.save_account(channel="ibm_quantum_platform",
                                          token="YOUR_TOKEN", overwrite=True)
     (or pass token=... straight into solve_assignment_qaoa).

HONEST EXPECTATION
------------------
On these small instances QAOA on real (noisy) hardware will most likely do WORSE
than neal -- near-term quantum is not a performance win here. The point is a
truthful demonstration: the SAME QUBO runs on a real quantum optimizer, judged by
the same exact evaluator. We report whatever number comes back.
"""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")

import numpy as np

from qiskit.primitives import StatevectorSampler
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

import hybrid as hyb
import matheuristic as mh


# --------------------------------------------------------------------------- #
# QUBO dict -> Qiskit QuadraticProgram                                         #
# --------------------------------------------------------------------------- #
def qubo_to_qp(qubo, name="assignment"):
    names = sorted({v for k in qubo for v in k})
    qp = QuadraticProgram(name)
    for v in names:
        qp.binary_var(v)
    linear, quadratic = {}, {}
    for (i, j), c in qubo.items():
        if i == j:
            linear[i] = linear.get(i, 0.0) + c
        else:
            quadratic[(i, j)] = quadratic.get((i, j), 0.0) + c
    qp.minimize(linear=linear, quadratic=quadratic)
    return qp


# --------------------------------------------------------------------------- #
# Build a QAOA instance on the requested backend                               #
# --------------------------------------------------------------------------- #
def make_qaoa(backend="aer", reps=1, maxiter=80, token=None, seed=42):
    """Return (qaoa, backend_label)."""
    if backend == "aer":
        pm = generate_preset_pass_manager(optimization_level=1,
                                          backend=AerSimulator())
        qaoa = QAOA(sampler=StatevectorSampler(seed=seed),
                    optimizer=COBYLA(maxiter=maxiter), reps=reps, transpiler=pm)
        return qaoa, "Aer statevector SIMULATOR (not real hardware)"

    if backend == "ibm":
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
        # token=None -> use the saved account
        service = (QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
                   if token else QiskitRuntimeService())
        qpu = service.least_busy(operational=True, simulator=False)
        pm = generate_preset_pass_manager(optimization_level=1, backend=qpu)
        qaoa = QAOA(sampler=SamplerV2(mode=qpu),
                    optimizer=COBYLA(maxiter=maxiter), reps=reps, transpiler=pm)
        return qaoa, f"IBM QPU [{qpu.name}] (REAL quantum hardware)"

    raise ValueError(f"backend must be 'aer' or 'ibm', got {backend!r}")


# --------------------------------------------------------------------------- #
# Solve the fleet assignment with QAOA, score with the exact oracle            #
# --------------------------------------------------------------------------- #
def solve_assignment_qaoa(ev: mh.Evaluator, backend="aer", reps=1, maxiter=80,
                          topk=25, token=None, seed=42, verbose=True):
    """QAOA (quantum) proposes assignments; the exact oracle scores them.
    Returns (best_plan, best_fuel, info)."""
    qubo, solo, P = hyb.build_assignment_qubo(ev)
    qp = qubo_to_qp(qubo)
    n_qubits = len(qp.variables)
    qaoa, label = make_qaoa(backend, reps, maxiter, token, seed)

    if verbose:
        print(f"  QAOA on {label}")
        print(f"  assignment QUBO: {n_qubits} qubits, reps={reps}, "
              f"maxiter={maxiter}")

    result = MinimumEigenOptimizer(qaoa).solve(qp)

    # QAOA returns a DISTRIBUTION of candidate bitstrings -- exactly what the
    # hybrid wants. Score the most probable ones exactly, keep the real best.
    names = [v.name for v in qp.variables]
    samples = sorted(result.samples, key=lambda s: -s.probability)
    best_plan, best_f, scored, seen = None, float("inf"), 0, set()
    for smp in samples:
        vd = {names[i]: int(round(smp.x[i])) for i in range(len(names))}
        assign = hyb.decode_assignment(vd, ev)
        key = tuple(tuple(sorted(assign[s.id])) for s in ev.scn.ships)
        if key in seen:
            continue
        seen.add(key)
        f, plan = hyb.exact_score(ev, assign)
        if f < best_f:
            best_f, best_plan = f, plan
        scored += 1
        if scored >= topk:
            break

    info = {"backend": label, "n_qubits": n_qubits,
            "assignments_scored": scored, "qaoa_best_energy": result.fval}
    return best_plan, best_f, info


def solve_on_hardware(ev: mh.Evaluator, backend_name=None, reps=1, maxiter=60,
                      shots=4096, topk=25, seed=42, verbose=True):
    """Run the assignment QUBO on a REAL IBM QPU, quota-economically.

    Strategy (standard for near-term hardware): optimise the QAOA parameters on
    the local simulator (free, many evaluations), then execute the ONE optimised
    circuit on the real QPU (a single job, minimal QPU time). The hardware
    measurement bitstrings are decoded into assignments and scored EXACTLY by the
    oracle -- identical to the neal/aer hybrids, only the sampler is real silicon.
    """
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit_optimization.converters import QuadraticProgramToQubo

    qubo, solo, P = hyb.build_assignment_qubo(ev)
    qp = qubo_to_qp(qubo)
    names = [v.name for v in qp.variables]
    n = len(names)

    # 1. optimise QAOA parameters on the simulator
    op, _ = QuadraticProgramToQubo().convert(qp).to_ising()
    pm_sim = generate_preset_pass_manager(optimization_level=1,
                                          backend=AerSimulator())
    qaoa = QAOA(sampler=StatevectorSampler(seed=seed),
                optimizer=COBYLA(maxiter=maxiter), reps=reps, transpiler=pm_sim)
    res = qaoa.compute_minimum_eigenvalue(op)

    # 2. bind the optimised parameters into the circuit -> measure -> transpile
    circ = res.optimal_circuit.assign_parameters(res.optimal_point)
    circ.measure_all()
    svc = QiskitRuntimeService()
    backend = (svc.backend(backend_name) if backend_name
               else svc.least_busy(operational=True, simulator=False))
    pm_hw = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa = pm_hw.run(circ)

    # 3. ONE job on real hardware
    if verbose:
        print(f"  submitting 1 job to REAL QPU [{backend.name}] "
              f"({n} qubits, {shots} shots)...")
    job = SamplerV2(mode=backend).run([isa], shots=shots)
    if verbose:
        print(f"  job id: {job.job_id()}  -- waiting for the quantum computer...")
    result = job.result()
    counts = result[0].data.meas.get_counts()

    # 4. decode hardware bitstrings -> assignments -> exact oracle score
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    best_plan, best_f, scored, seen = None, float("inf"), 0, set()
    for bits, _cnt in ranked:
        vd = {names[i]: int(bits[-(i + 1)]) for i in range(n)}
        assign = hyb.decode_assignment(vd, ev)
        key = tuple(tuple(sorted(assign[s.id])) for s in ev.scn.ships)
        if key in seen:
            continue
        seen.add(key)
        f, plan = hyb.exact_score(ev, assign)
        if f < best_f:
            best_f, best_plan = f, plan
        scored += 1
        if scored >= topk:
            break

    usage = getattr(job, "usage_estimation", None)
    info = {"backend": backend.name, "n_qubits": n, "job_id": job.job_id(),
            "distinct_bitstrings": len(counts), "assignments_scored": scored,
            "usage": usage}
    return best_plan, best_f, info


if __name__ == "__main__":
    import argparse

    import oracle
    import scenario as scen_mod

    p = argparse.ArgumentParser(description="Run the fleet assignment on QAOA.")
    p.add_argument("--backend", choices=["aer", "ibm"], default="aer")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ships", type=int, default=2, help="smaller = fewer qubits")
    p.add_argument("--missions", type=int, default=4)
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--maxiter", type=int, default=60)
    p.add_argument("--token", default=None, help="IBM Quantum API token")
    args = p.parse_args()

    scn = scen_mod.build_scenario(args.seed, n_ships=args.ships,
                                  n_missions=args.missions)
    tabs = oracle.get_tables(scn, verbose=False)
    ev = mh.Evaluator(scn, tabs)

    plan, f, info = solve_assignment_qaoa(
        ev, backend=args.backend, reps=args.reps, maxiter=args.maxiter,
        token=args.token, seed=args.seed + 1)

    # references
    pe, fe, _ = mh.exhaustive(ev)
    _, nf, _ = hyb.solve_hybrid(ev, num_reads=200, seed=1)   # neal hybrid
    print()
    print(f"  QAOA hybrid ({args.backend}): {f:.2f} t   "
          f"({info['assignments_scored']} assignments scored)")
    print(f"  neal hybrid              : {nf:.2f} t")
    print(f"  exact optimum            : {fe:.2f} t   "
          f"QAOA gap {(f-fe)/fe*100:+.2f}%")
    if plan is not None:
        print(mh.describe_plan(ev, plan))
