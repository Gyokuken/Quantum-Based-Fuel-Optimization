"""HONEST AUDIT: run every solver across MANY seeds on the same 3x4 route QUBO
(the one the qseed-11 diagram used) and report the full distribution -- so the
cherry-picking is visible. No best-of, no selected seed: every run counted."""
import warnings, types
warnings.filterwarnings("ignore")
import numpy as np
import quantum_gate as qg

a = types.SimpleNamespace(problem="route", rows=3, cols=4, storms=1, seed=2,
                          cruise=16.0, distance=600.0, ship_type="Offshore_Patrol")
qubo, decode, meta, ctx = qg.build_route_problem(a)
qp = qg.qubo_to_qp(qubo)
dp = ctx["dp_fuel"]
N = 15
print(f"3x4 route, {N} seeds each. Exact optimum = {dp:.2f} t (path {ctx['dp_path']})\n")
print(f"{'solver':<8}{'hit opt':>9}{'feasible':>10}{'mean gap':>10}{'worst gap':>11}")
print("-" * 48)

def run_all(name, fn, seeds):
    hits = feas = 0; gaps = []
    for s in seeds:
        path, fuel, _ = decode(fn(s))
        if path is not None:
            feas += 1
            g = (fuel - dp) / dp * 100
            gaps.append(g)
            if abs(g) < 1e-6: hits += 1
    mg = f"{np.mean(gaps):+.1f}%" if gaps else "n/a"
    wg = f"{max(gaps):+.1f}%" if gaps else "n/a"
    print(f"{name:<8}{hits}/{N:<7}{feas}/{N:<8}{mg:>10}{wg:>11}")

run_all("neal", lambda s: qg.run_neal(qubo, seed=s), range(N))
run_all("GSA", lambda s: qg.run_gsa(qubo, seed=s, restarts=20), range(N))
run_all("QAOA", lambda s: qg.run_qaoa(qp, 2, 100, seed=s), range(N))
run_all("VQE", lambda s: qg.run_vqe(qp, meta["n_qubits"], 1, 200, seed=s), range(N))
print("\nqseed 11 (the diagram I published) vs this full spread tells the story.")
