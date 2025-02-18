# Catan Conqueror: Intelligent Bot for Settlers of Catan

---

### Project Overview  
An intelligent bot designed to master the classic board game *Settlers of Catan*. This project aims to implement a bot that can compete against human players by leveraging both strategy and probabilistic decision-making, incorporating the elements of chance (e.g., dice rolls) and strategic planning (e.g., resource management, negotiation, and route optimization) inherent in the game.

**Contributors**  
- Charlie Gordon  
- Caroline Cahilly  
- Proud Mpala

** Project Report ***
[CS238__Final_Report.pdf](https://github.com/user-attachments/files/18841691/CS238__Final_Report.pdf)


---

### 🧭 Goal

Our objective is to develop a bot capable of competing at a level comparable to human players in *Catan*. We benchmark performance against:
- A **random-move bot** baseline.
- **Human-level competition** where each team member will play the bot multiple times. The target win rate is set to >1/n (where *n* is the number of players), indicating human-competitive performance.

**Why It’s Interesting**  
The game dynamics of *Catan* involve complex decision-making under uncertainty, making this a fascinating problem for AI development. This project blends AI, game theory, and decision modeling in a multi-agent environment.

---

### 🧠 Decision-Making Process

The bot’s decisions are modeled as a **Sequential Decision Problem**, with actions affecting game states, opponents, and the bot's path to victory.  
- **States**: The bot’s resources, board position, visible opponent positions, and a probabilistic model of resource generation.
- **Actions**: Building (settlements, cities, roads), trading (with players or bank), strategic moves like using Development Cards or placing the robber.
- **Transitions**: Determined by dice rolls, trade outcomes, and resource constraints.
- **Rewards**: Points toward winning the game, with intermediate rewards from strategic positioning, resource control, or robber placement.

---

### 🎲 Key Sources of Uncertainty

- **Dice Rolls**: Randomly determine resource generation.
- **Opponent Behavior**: Unpredictable actions like trade offers and robber placements require adaptability.
- **Limited Information**: Only partial visibility into opponents’ resources adds complexity.

---

### ⚙️ Solution Sketch

Our initial approach simplifies the problem to a 1v1 game, modeling it as a **multi-agent POMDP** where each agent seeks to maximize points. The bot’s decision-making combines POMDP-based strategy with heuristic approaches for resource and trade management.

---

### 📚 Resources Used  
- [Catanatron Colab](https://colab.research.google.com/github/bcollazo/catanatron/blob/master/catanatron_experimental/catanatron_experimental/Overview.ipynb)
- [Stanford CS221 Posters and Reports](https://web.stanford.edu/class/archive/cs/cs221/cs221.1192/2018/restricted/posters/wlauer/poster.pdf)

---

### 🤝 Contribute to Catan Conqueror  
This project is open for contributions, feedback, and suggestions. Help us build the ultimate *Catan* bot!
