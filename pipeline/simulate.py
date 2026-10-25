"""Simulated shooters with known truth, for tests and the power curve."""

import numpy as np


def simulate_shooter(rng, n_games=60, shots_per_game=12, p=0.46, game_sd=0.0, boost=0.0, k=1):
    """Return (made, game) arrays for one simulated player.

    - Shots per game vary (Poisson around shots_per_game, at least 1).
    - Each game has its own make probability p + Normal(0, game_sd), so some
      nights are better than others even without a hot hand.
    - Hot hand: after k makes in a row in the same game, the make probability
      goes up by `boost` (boost = 0 means no hot hand).
    """
    made, game = [], []
    for g in range(n_games):
        n = max(1, rng.poisson(shots_per_game))
        p_game = float(np.clip(p + rng.normal(0, game_sd), 0.05, 0.95)) if game_sd else p
        streak = 0
        for _ in range(n):
            p_shot = min(p_game + boost, 0.99) if streak >= k else p_game
            hit = int(rng.random() < p_shot)
            streak = streak + 1 if hit else 0
            made.append(hit)
            game.append(g)
    return np.array(made, dtype=np.int8), np.array(game)
