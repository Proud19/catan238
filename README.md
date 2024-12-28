# Catan Conqueror: AI Agents for Two-Player Settlers of Catan

## Overview
**Catan Conqueror** is a framework for developing and evaluating AI agents to play a two-player version of the board game *Settlers of Catan*. This project implements and benchmarks multiple agents using techniques such as Q-learning, custom value functions, and lookahead with rollouts.

## Rules and Gameplay
The game is based on the standard rules of *Settlers of Catan* with the following modifications:
- **Two-player mode**: Only two players are supported.
- **Fixed board initialization**: The board setup (hexes, numbers, and robber placement) is the same for every game.
- **No ports**: Ports are removed from the game.
- **No interplayer trading**: Players cannot trade resources directly with each other.

Players compete to be the first to reach **10 victory points** by building settlements, cities, and roads, as well as acquiring development cards.

## Implemented Agents
This repository includes five distinct agents:

### 1. **Random Agent**
- Makes moves randomly based on valid actions.
- Serves as a baseline for evaluating other agents.

### 2. **Custom Value Function Agent**
- Uses a custom heuristic to evaluate game states and select actions greedily.
- Evaluates settlement locations, production potential, and future expansion options.

### 3. **Q-Learning Agent**
- Implements a reinforcement learning approach with:
  - **State representation** capturing game progress, opponent status, and board state.
  - **Experience replay** for stable learning.
  - **Reward shaping** to encourage long-term strategies and victory.
  - **Q-table pruning** to focus learning on relevant states.
- Trained over 15,000 iterations and achieves an 85% win rate against the Custom Value Function agent.

### 4. **Lookahead-with-Rollouts Agent**
- Uses simulated rollouts to evaluate future actions.
- Can operate with either **random** or **greedy policies** during rollouts.
- Allows customization of rollout depth to balance computation time and performance.

### 5. **Human Agent**
- Allows a human player to compete against AI agents via a graphical user interface (GUI).

## Experiments and Results
### 1. **Agent vs. Agent Matches**
- All agents were tested against each other in 200 simulations, alternating first-player advantages.
- The **Q-Learning Agent** performed best, with a win rate of 76% against its trainer, the custom function value agent.

### 2. **Ablation Study for Rollout Depth**
- Deeper rollouts beyond depth 5 did not significantly improve performance but increased computation time.

### 3. **Rollout Policy Comparisons**
- Greedy policies for both agents and opponents yielded the highest win rates and efficiency.

See `docs/` for more details.

## Key Files
- `game.py`: Entry point to run experiments and simulations.
- `agents.py`: Contains implementations for each AI agent.
- `draw.py`: GUI implementation.
- `gameConstants.py`: Game constants (e.g., valid actions).
- `board.py`: Game state.

## Future Work
- **Randomized board setups** to generalize strategies.
- **Port mechanics** and **player trading** for expanded gameplay.
- **Multi-agent dynamics** for larger player groups.
- **Improved opponent modeling** to handle dynamic strategies.

## References
1. Collazo, B. (2024). *Catanatron: An AI for Settlers of Catan*. [GitHub Repository](https://github.com/bcollazo/catanatron).
2. Kaplan-Nelson, S., Leung, S., & Troccoli, N. (2014). *An AI Agent for Settlers of Catan*. [GitHub Repository](https://github.com/skleung/cs221).

---

### 🤝 Contribute to Catan Conqueror  
This project is open for contributions, feedback, and suggestions. Help us build the ultimate *Catan* bot!
Developed by Caroline Cahilly, Charlie Gordon, and Proud Mplala at Stanford University.