"""
gsa.py  --  Phase 2d: the Gravitational Search Algorithm (a NEW optimizer family).

So far every optimizer we used is either annealing (SA / neal / D-Wave) or
gate-model (QAOA / VQE). GSA is a completely different idea -- a *swarm*
metaheuristic inspired by NEWTON'S LAW OF GRAVITY.

THE PHYSICS ANALOGY (Rashedi, Nezamabadi-pour & Saryazdi, 2009)
--------------------------------------------------------------
* Each candidate solution is an "agent" = a mass floating in the search space.
* An agent's MASS is set by how GOOD its solution is (lower fuel => heavier).
* Heavy masses pull lighter ones toward them via simulated gravity:
      F = G * (M_i * M_j) / R      (Newton's law, R = distance between agents)
* So good solutions attract the swarm; agents accelerate toward them and the
  population converges on the best region.
* The gravitational constant G SHRINKS over time (G(t) = G0 * exp(-alpha*t/T)),
  which turns broad early EXPLORATION into fine late EXPLOITATION -- the same
  explore->exploit arc simulated annealing gets from its cooling schedule.

TWO FLAVOURS
------------
* Continuous GSA  -> optimises a real-valued variable. PERFECT for the SPEED
  problem (speed is continuous) -- a direct rival to our simulated annealing.
* Binary GSA (BGSA, Rashedi 2010) -> optimises 0/1 variables, so it can solve a
  QUBO. Velocity drives a transfer function S(v)=|tanh(v)| that gives each bit a
  probability of flipping. This lets GSA slot into our solver comparison next to
  neal / QAOA / VQE via the GSASampler adapter below.

References:
  Rashedi et al. (2009) "GSA: A Gravitational Search Algorithm", Information Sciences
  Rashedi et al. (2010) "BGSA: Binary Gravitational Search Algorithm", Natural Computing
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-12


# --------------------------------------------------------------------------- #
# Core GSA step shared by both flavours: positions X -> accelerations          #
# --------------------------------------------------------------------------- #
def _masses(fitness):
    """Map fitness (to MINIMISE) -> normalised masses in [0,1] summing to 1.
    Best (lowest) fitness -> mass 1; worst -> mass 0."""
    best, worst = fitness.min(), fitness.max()
    if worst - best < _EPS:
        m = np.ones_like(fitness)
    else:
        m = (worst - fitness) / (worst - best)     # low fitness -> high mass
    return m / (m.sum() + _EPS)


def _accelerations(X, M, fitness, G, kbest, rng):
    """GSA acceleration on every agent from the Kbest heaviest agents.
    a_i = G * sum_j rand_ij * M_j/(R_ij+eps) * (X_j - X_i).  (mass M_i cancels.)

    Fully vectorised: pairwise differences + one einsum, no Python loop over
    agents -- essential so the benchmark harness can run many seeds/sizes."""
    n_agents = X.shape[0]
    order = np.argsort(fitness)                  # ascending: best (heaviest) first
    mask = np.zeros(n_agents)
    mask[order[:max(1, kbest)]] = 1.0            # only Kbest agents exert force
    D = X[None, :, :] - X[:, None, :]            # D[i,j] = X_j - X_i        (N,N,dim)
    R = np.linalg.norm(D, axis=2) + _EPS         # pairwise distance         (N,N)
    W = rng.random((n_agents, n_agents)) * (M * mask)[None, :] / R   # weights (N,N)
    return G * np.einsum("ij,ijk->ik", W, D)     # a[i] = G * sum_j W_ij D_ij


def _kbest(t, iters, n_agents):
    """Number of attracting agents: linearly N -> 1 over the run (elitism)."""
    frac = 1.0 - t / max(1, iters)          # 1 -> 0
    return int(round(1 + (n_agents - 1) * frac))


# --------------------------------------------------------------------------- #
# Continuous GSA  (for the speed problem)                                       #
# --------------------------------------------------------------------------- #
def gsa_minimize(objective, bounds, *, n_agents=30, iters=200,
                 g0=100.0, alpha=20.0, seed=0, vectorized=False):
    """Minimise objective(x) over a box `bounds` (list of (lo,hi)) with GSA.
    If `vectorized`, objective takes the whole (N,dim) array and returns (N,)
    fitness in one call (much faster when each eval is an ML prediction).
    Returns (best_x, best_fitness, history)."""
    rng = np.random.default_rng(seed)
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    dim = len(bounds)

    X = lo + rng.random((n_agents, dim)) * (hi - lo)
    V = np.zeros((n_agents, dim))
    best_x, best_f = None, np.inf
    history = {"best": [], "mean": []}                    # best-so-far + swarm mean

    for t in range(iters):
        fitness = (np.asarray(objective(X)) if vectorized
                   else np.array([objective(x) for x in X]))
        i = int(np.argmin(fitness))
        if fitness[i] < best_f:
            best_f, best_x = float(fitness[i]), X[i].copy()
        history["best"].append(best_f)
        history["mean"].append(float(np.mean(fitness)))   # swarm "cloud" collapsing

        M = _masses(fitness)
        G = g0 * np.exp(-alpha * t / iters)
        a = _accelerations(X, M, fitness, G, _kbest(t, iters, n_agents), rng)
        V = rng.random((n_agents, dim)) * V + a           # inertia + accel
        X = np.clip(X + V, lo, hi)                        # move, stay in box

    return best_x, best_f, history


# --------------------------------------------------------------------------- #
# Binary GSA  (for QUBOs)                                                       #
# --------------------------------------------------------------------------- #
def _qubo_matrix(qubo):
    """Turn a pyqubo QUBO dict {(vi,vj):c} into (names, Q) with energy = x^T Q x."""
    names = sorted({v for k in qubo for v in k})
    idx = {name: i for i, name in enumerate(names)}
    n = len(names)
    Q = np.zeros((n, n))
    for (i, j), c in qubo.items():
        Q[idx[i], idx[j]] += c
    return names, Q


def bgsa_qubo(qubo, *, n_agents=60, iters=150, g0=100.0, alpha=15.0, seed=0):
    """Minimise a QUBO with Binary GSA. Returns (best_sample_dict, energy, history)."""
    names, Q = _qubo_matrix(qubo)
    n = len(names)
    rng = np.random.default_rng(seed)

    def energies(Xb):                                    # batch energy x^T Q x
        return np.einsum("ni,ij,nj->n", Xb, Q, Xb)

    X = rng.integers(0, 2, size=(n_agents, n)).astype(float)
    V = np.zeros((n_agents, n))
    best_x, best_e = None, np.inf
    history = []

    for t in range(iters):
        fitness = energies(X)
        i = int(np.argmin(fitness))
        if fitness[i] < best_e:
            best_e, best_x = float(fitness[i]), X[i].copy()
        history.append(best_e)

        M = _masses(fitness)
        G = g0 * np.exp(-alpha * t / iters)
        a = _accelerations(X, M, fitness, G, _kbest(t, iters, n_agents), rng)
        V = rng.random((n_agents, n)) * V + a
        # Transfer function: |tanh(v)| = probability of flipping the bit (BGSA).
        flip = rng.random((n_agents, n)) < np.abs(np.tanh(V))
        X = np.where(flip, 1.0 - X, X)

    sample = {names[k]: int(best_x[k]) for k in range(n)}
    return sample, best_e, history


# --------------------------------------------------------------------------- #
# Sampler adapter: makes BGSA look like a dwave/neal sampler for backends.py    #
# --------------------------------------------------------------------------- #
class GSASampler:
    """Minimal dimod-style sampler so BGSA drops into the QUBO comparison.
    Runs `num_reads` independent BGSA searches and returns them as a SampleSet
    (lowest energy first), matching neal/tabu's interface."""

    def __init__(self, n_agents=60, iters=150):
        self.n_agents = n_agents
        self.iters = iters

    def sample_qubo(self, qubo, num_reads=8, seed=0, **_):
        import dimod
        names, Q = _qubo_matrix(qubo)
        samples, energies = [], []
        for r in range(max(1, num_reads)):
            s, e, _ = bgsa_qubo(qubo, n_agents=self.n_agents,
                                iters=self.iters, seed=seed + r)
            samples.append([s[nm] for nm in names])
            energies.append(e)
        return dimod.SampleSet.from_samples(
            (np.array(samples), names), vartype="BINARY", energy=energies)
