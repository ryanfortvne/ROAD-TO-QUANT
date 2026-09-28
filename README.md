# Quantitative Strategy Evaluation & Research Standards

This repository documents my ongoing quantitative research, strategy development, and risk management frameworks. It serves as a central log for active projects, backtesting criteria, and execution standards.

---

## 🎯 Current Research Standards

The thresholds below represent my current working definitions for evaluating strategy viability. They are designed to assess performance holistically across return profile, statistical confidence, drawdown control, and execution sustainability.

> **Note:** These criteria reflect my current research baseline rather than universal industry standards. They are continuously tested and refined as my analytical framework evolves.

| Category | Metric | Current Criterion |
| :--- | :--- | :--- |
| **Return Profile** | Expected Value / Expectancy | `> 0.00 R` |
| | Payoff Ratio | `> 1.50 : 1` |
| | Profit Factor | `≥ 1.00` |
| **Consistency & Risk** | Risk of Ruin | `< 1.00%` |
| | Rolling 6-Month Sharpe Ratio | `≥ 0.50` |
| | Maximum Drawdown | `< 15.00%` |
| | Max Consecutive Drawdown Months | `< 3 Months` |
| | Default Risk per Trade | `0.74%` of starting capital |
| **Statistical Reliability** | Standard Error / Mean | `< 20.00%` |
| | Efficiency Ratio | `> 0.20` |
| **Recent Performance Tracking** | Recent Win Rate | `≥ 45.00%` |
| | Recent Expectancy | `≥ 0.20 R` |

---

## 🧠 Evaluation Framework

No single metric is sufficient to declare a strategy viable. This evaluation model tests a system across multiple dimensions:

$$\text{Return} \longrightarrow \text{Consistency} \longrightarrow \text{Statistical Reliability} \longrightarrow \text{Risk Management} \longrightarrow \text{Robustness} \longrightarrow \text{Execution}$$

* **Return & Payoff Structure:** Ensures the edge is real and positive over time without relying on extreme, unrepeatable outliers.
* **Risk & Drawdown Limits:** Prevents catastrophic capital decay; a high-return strategy with severe drawdowns is fundamentally non-viable.
* **Statistical Rigor:** Validates that observed performance is statistically significant rather than an artifact of curve-fitting or noise.

---

## 🔬 Active Projects

### 📊 Statistical Research
* **Kill Criterion Framework:** A systematic evaluation framework designed to automatically flag or decommission strategies failing core expectancy, payoff ratio, risk of ruin, Sharpe, or drawdown thresholds.

---

*More projects and research models will be added as development progresses.*
