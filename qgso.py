"""
qgso.py -- Quantum-inspired Gravitational Search Optimizer (QGSO / QGSA).

THE 'QUANTUM' TWIST ON GSA
--------------------------
Plain binary GSA (BGSA, gsa.py) keeps each agent as a definite 0/1 string and
FLIPS bits with probability |tanh(velocity)|. QGSO replaces the string with a
register of QUBITS: one rotation angle theta per variable, where

        P(bit = 1) = sin^2(theta) .

The whole swarm therefore lives in SUPERPOSITION. Each iteration every agent is
MEASURED (collapsed) into a concrete binary string that gets evaluated -- so
the same agent can sample different solutions on different iterations, which is
the quantum-inspired source of diversity.

The Newtonian machinery of GSA is unchanged: good solutions are 'heavy', heavy
agents attract the rest (F = G M_i M_j / R), and G cools over time. That
attraction produces a velocity per qubit; the velocity then drives a QUANTUM
ROTATION GATE (Han & Kim 2002): each qubit's angle is rotated toward |1> or
|0> along the gravitational pull, by a bounded amount. As G cools the rotations
shrink and the angles settle near 0 or pi/2 -- the superposition 'collapses'
onto a solution (QGSO's exploit phase, the analogue of GSA's late cooling).

WHY THIS FILE EXISTS
--------------------
To answer, honestly, "does the quantum-inspired variant actually beat plain
GSA, or is it just a fancier name?" It is benchmarked at EQUAL budget against
neal / tabu / gsa on the same route QUBO (exact DP ground truth, many seeds,
mean +/- std) in benchmark.py. Structure is kept parallel to bgsa_qubo so the
ONLY difference measured is the quantum rotation-gate update vs the bit-flip.

References: Rashedi et al. 2009 (GSA), 2010 (BGSA); Han & Kim 2002 (quantum
rotation gate / QEA); Nezamabadi-pour 2015 (quantum-inspired binary GSA).
"""

from __future__ import annotations

import numpy as np

import gsa                      # reuse _masses, _accelerations, _kbest, _qubo_matrix

_HALF_PI = np.pi / 2.0
# Clip angles so a qubit never fully collapses -- always keeps a few % of
# superposition, preserving diversity (standard in quantum-inspired EAs).
_THETA_MIN = 0.02 * _HALF_PI
_THETA_MAX = 0.98 * _HALF_PI


def qgso_qubo(qubo, *, n_agents=60, iters=150, g0=100.0, alpha=15.0,
              rot=0.04 * np.pi, seed=0):
    """Minimise a QUBO with Quantum-inspired GSA.

    rot : base rotation-gate angle (the one QGSO-specific knob; the effective
          rotation is rot * tanh(velocity), so it is modulated by gravity and
          shrinks as G cools).
    Returns (best_sample_dict, best_energy, history_of_best).
    """
    names, Q = gsa._qubo_matrix(qubo)
    n = len(names)
    rng = np.random.default_rng(seed)

    def energies(Xb):                                   # batch energy x^T Q x
        return np.einsum("ni,ij,nj->n", Xb, Q, Xb)

    theta = rng.uniform(_THETA_MIN, _THETA_MAX, size=(n_agents, n))  # qubit angles
    V = np.zeros((n_agents, n))
    best_x, best_e = None, np.inf
    history = []

    for t in range(iters):
        p1 = np.sin(theta) ** 2                          # P(bit = 1) per qubit
        X = (rng.random((n_agents, n)) < p1).astype(float)   # MEASURE (collapse)
        fitness = energies(X)
        i = int(np.argmin(fitness))
        if fitness[i] < best_e:
            best_e, best_x = float(fitness[i]), X[i].copy()
        history.append(best_e)

        M = gsa._masses(fitness)
        G = g0 * np.exp(-alpha * t / iters)
        a = gsa._accelerations(X, M, fitness, G,
                               gsa._kbest(t, iters, n_agents), rng)
        V = rng.random((n_agents, n)) * V + a            # inertia + gravity
        # Quantum rotation gate: rotate each qubit toward |1> (theta -> pi/2)
        # or |0> (theta -> 0) along the gravitational pull sign(V), by a bounded
        # amount rot*tanh(V). This is QGSO's update, replacing BGSA's bit-flip.
        theta = np.clip(theta + rot * np.tanh(V), _THETA_MIN, _THETA_MAX)

    sample = {names[k]: int(best_x[k]) for k in range(n)}
    return sample, best_e, history


class QGSOSampler:
    """dimod-style sampler so QGSO drops into the benchmark exactly like GSA
    (independent restarts, best kept). Same interface as gsa.GSASampler."""

    def __init__(self, n_agents=100, iters=300, rot=0.04 * np.pi):
        self.n_agents = n_agents
        self.iters = iters
        self.rot = rot

    def sample_qubo(self, qubo, num_reads=8, seed=0, **_):
        import dimod
        names, _ = gsa._qubo_matrix(qubo)
        samples, energies = [], []
        for r in range(max(1, num_reads)):
            s, e, _ = qgso_qubo(qubo, n_agents=self.n_agents, iters=self.iters,
                                rot=self.rot, seed=seed + r)
            samples.append([s[nm] for nm in names])
            energies.append(e)
        return dimod.SampleSet.from_samples((np.array(samples), names),
                                            vartype="BINARY", energy=energies)


if __name__ == "__main__":
    # Sanity on a tiny QUBO: minimise -x0 - x1 + 2 x0 x1 + x2  (opt = -1)
    q = {("x0", "x0"): -1.0, ("x1", "x1"): -1.0, ("x2", "x2"): 1.0,
         ("x0", "x1"): 2.0}
    s, e, _ = qgso_qubo(q, n_agents=40, iters=80, seed=1)
    print(f"QGSO tiny QUBO: {s}, energy {e:.3f}  (expect -1)")
