# Rubik-s-Cube-Simulator-and-Solver
## Overview
The Rubik-s-Cube-Simulator-and-Solver project showcases a custom Rubik's cube simulation and a novel algorithm for solving the puzzle, developed entirely from scratch.

## Features
- Rubik's cube simulation model
- Custom solving algorithm (currently in progress)

## Getting Started
1. Clone the repository:
   ```
   git clone https://github.com/ngrjchk/Rubik-s-Cube-Simulator-and-Solver.git
   ```
2. Navigate to the project folder.
3. Ensure Python is installed.
4. Install the required packages by running `pip install -r requirements.txt`
1. Open the provided notebooks to explore simulation and solving techniques.

## Usage
- Use `./Simulators/cube_simulator_full.py` to test the simulator.
- Use `./Notebooks/solver.ipynb` to test the solver (currently in progress)
- Use `./Notebooks/table_generators.ipynb` for generating and exploring useful pre-computed tables.

## License
This project is licensed under the Apache License, Version 2.0. See the LICENSE file for details.

## Appendix

### Detailed Report on my "Interpolation" idea for the Rubik's Cube Solver

Firstly, I think that the term "interpolation" aptly captures the essence of my approach: **interweaving and combining individually optimized move sequences to achieve a global solution for the Rubik's Cube.**

**1. Introduction:**

My core idea is to solve the Rubik's Cube not as a single, monolithic problem, but as a set of smaller, independent subproblems, one for each piece. For each subproblem (solving a specific edge), I pre-calculate an **isolated move sequence** that optimally solves that piece *in isolation*, without considering the impact on other pieces.

The "interpolation" aspect comes into play when I attempt to **combine** these isolated sequences into a single, coherent sequence that solves the entire cube. This combination is not a simple concatenation of sequences; instead, I am selecting moves from these isolated sequences at each step, aiming to find a path through a graph of moves that minimizes unwanted "side effects" on other pieces.

**2. Detailed Explanation of the Interpolation Algorithm (Explained for a White cross):**

My algorithm uses a graph-based recursive approach to achieve this "interpolation" of isolated move sequences. Here's a breakdown of the key elements:

**2.1. Isolated Move Sequences (Columns):**

*   For each of the four cross edges (Orange-White, Blue-White, Red-White, Green-White), I have precomputed **columns** of moves. Each column represents an isolated move sequence that solves only the corresponding cross edge piece, ignoring the rest of the cube.
*   These sequences are pre-calculated to be optimal *for their individual piece*.
*   Example: For the Orange-White edge, the isolated sequence might be `["R", "F'", "U"]`.

**2.2. Graph Representation and Recursive Search:**

*   I envision a graph where **nodes** are individual moves from all isolated move sequences.
*   **Edges:**
    *   **Downward Edges:** Within each column, moves are linked downwards, representing the order within the isolated sequence.
    *   **Inter-Column Edges:**  Initially, I consider bidirectional connections between moves from different columns (except for the downward column edges).
*   **Recursive Branching:** I employ recursion to explore paths through this graph.
    *   **Depth:** Recursion depth corresponds to the move number in the potential solution sequence.
    *   At each depth, I select a "freely available move" from one of the columns.
    *   Recursion branches explore different choices of moves at each depth.

**2.3. "Freely Available Move" Concept:**

*   At each recursion depth, for each column, I determine the "freely available move." This is the next move in the column's isolated sequence that hasn't been used at a shallower depth in the *current* recursive branch.
*   This ensures I am progressing through each isolated sequence in order.

**2.4. Side Effect Minimization:**

*   The core of my "interpolation" strategy is the **side effect count**. This is a heuristic (?) to guide the search towards combinations of moves that minimize disruption to other cross edge pieces while solving the current piece.
*   **Side Effect Calculation:** For a candidate move `m` (from column `C1` for piece `P1`):
    *   I consider all *other* cross edge pieces (and their columns).
    *   For each other piece `P2` (column `C2`), I find its "freely available move" `n`.
    *   If `m` is *not* the same as `n`, I check if applying `m` has a "negative side effect" on piece `P2`, based on seeing if `m` moves `P2` "farther" from its solved state, meaning the minimum path length has increased. If there is a negative side effect, I increment the side effect count for `m`.
    *   If `m` *is* the same as `n`, there's no side effect counted for piece `P2`, because `m` is in favour of `P2`'s isolated solution path.

*   **Guiding the Search:** The side effect count is used to guide my recursive search. I would ideally prefer to explore branches with moves that have lower side effect counts, hoping to find a combination of moves that solves the entire cross with minimal disruption.

**2.5. Solved Condition:**

*   My Rubik's Cube simulator is used at each recursion depth to check if the cross is solved after applying the sequence of moves in the current branch. This determines if a branch has found a valid solution.
