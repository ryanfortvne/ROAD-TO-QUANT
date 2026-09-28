from pathlib import Path
import numpy as np
import pandas as pd


def load_and_prepare_simple_trades() -> pd.DataFrame:
    file_path_str = input("Enter path to trade file (CSV or XLSX/XLS): ").strip().strip("'\"")
    path = Path(file_path_str)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path.resolve()}")

    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Must be .csv or .xlsx")

    # Normalize column names to lowercase
    df.columns = df.columns.str.strip().str.lower()

    # Rename common alternative column names automatically
    col_mappings = {
        "symbol": "pair", "ticker": "pair", "asset": "pair",
        "profit": "pnl", "profit/loss": "pnl", "net_pnl": "pnl", "gain": "pnl",
        "time": "date", "timestamp": "date", "close_time": "date"
    }
    df = df.rename(columns=col_mappings)

    # tells which column might be missing or not properly mapped
    required = {"date", "pnl"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"Input file is missing required columns: {missing}.")


    # Convert dates and sort chronologically
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # User inputs for reconstructing account state
    print("\n--- Account Configuration ---")
    initial_capital = float(input("Enter starting account capital: "))
    risk_per_trade = float(input("Enter dollar risk per trade [Press Enter for 0.74% of starting capital]: ") or (initial_capital * 0.0074))

    # 1. Auto-calculate cumulative equity
    df["equity"] = initial_capital + df["pnl"].cumsum()

    # 2. Auto-calculate R-multiple 
    if "r_multiple" not in df.columns:
        df["r_multiple"] = df["pnl"] / risk_per_trade

    return df


def calculate_metrics_and_eval_kill_criteria(
    df: pd.DataFrame,
    backtest_win_rate_mean: float = 0.55,
    backtest_win_rate_std: float = 0.05,
    backtest_ci_low: float = 0.20,
    est_transaction_cost: float = 0.0002,
    sharpe_lower_bound: float = 0.50,
    max_drawdown_limit: float = 0.15,
    max_dd_months_limit: int = 3,
    max_slippage_pct_increase: float = 0.30,
) -> dict:
    """Evaluates all baseline, statistical, rolling, and execution kill criteria."""
    r = df["r_multiple"].to_numpy()
    pnl = df["pnl"].to_numpy()
    equity = df["equity"].to_numpy()
    n_trades = len(r)

    if n_trades == 0:
        raise ValueError("Trade log is empty.")

   
    # 1. BASELINE STATISTICAL CHECKS(what i consider ideal)

    mean_expectancy = r.mean()
    sample_std = r.std(ddof=1) if n_trades > 1 else 0.0
    standard_error = sample_std / np.sqrt(n_trades) if n_trades > 0 else 0.0
    se_to_mean_ratio = (standard_error / abs(mean_expectancy)) if mean_expectancy != 0 else np.inf

    total_net_pnl = abs(pnl.sum())
    total_gross_movement = np.abs(pnl).sum()
    efficiency_ratio = (total_net_pnl / total_gross_movement) if total_gross_movement > 0 else 0.0

    wins = r[r > 0]
    losses = np.abs(r[r < 0])
    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = losses.mean() if len(losses) > 0 else 1e-9
    payoff_ratio = avg_win / avg_loss

    win_rate = (r > 0).mean()
    loss_rate = 1.0 - win_rate
    if win_rate > 0 and payoff_ratio > 0:
        edge = (win_rate * payoff_ratio) - loss_rate
        risk_of_ruin = ((1 - edge) / (1 + edge)) ** 10 if edge > 0 else 1.0
        risk_of_ruin = max(0.0, min(1.0, risk_of_ruin))
    else:
        risk_of_ruin = 1.0

    
    # 2. ROLLING & DRAWDOWN CHECKS
    df_daily = df.set_index("date")["equity"].resample("D").last().ffill().pct_change().dropna()
    if len(df_daily) > 180:
        rolling_6m_returns = df_daily.tail(180)
        daily_sharpe = rolling_6m_returns.mean() / (rolling_6m_returns.std() + 1e-9)
        rolling_6m_sharpe = daily_sharpe * np.sqrt(252)
    else:
        rolling_6m_sharpe = (df_daily.mean() / (df_daily.std() + 1e-9)) * np.sqrt(252) if len(df_daily) > 1 else 0.0

    recent_sample_size = min(50, n_trades)
    recent_r = r[-recent_sample_size:]
    recent_win_rate = (recent_r > 0).mean()
    recent_expectancy = recent_r.mean()

    profit_factor = wins.sum() / max(losses.sum(), 1e-9)

    running_max = np.maximum.accumulate(equity)
    drawdowns = (running_max - equity) / running_max
    current_drawdown = drawdowns[-1]
   

    df_monthly = df.set_index("date")["equity"].resample("ME").last().ffill()
    monthly_peaks = np.maximum.accumulate(df_monthly)
    monthly_dds = (monthly_peaks - df_monthly) / monthly_peaks
    
    consecutive_dd_months = 0
    for dd in monthly_dds[::-1]:
        if dd > 0.05:
            consecutive_dd_months += 1
        else:
            break


    # 3. EVALUATE KILL CRITERIA CHECKS
  
    checks = {
        "1. Positive Expectancy": (mean_expectancy > 0, f"Current: {mean_expectancy:.3f}R"),
        "2. Standard Error < 20% Mean": (se_to_mean_ratio < 0.20, f"SE Ratio: {se_to_mean_ratio*100:.1f}%"),
        "3. Efficiency Ratio > 0.20": (efficiency_ratio > 0.20, f"Current: {efficiency_ratio:.2f}"),
        "4. Payoff Ratio > 1.5:1": (payoff_ratio > 1.5, f"Current: {payoff_ratio:.2f}:1"),
        "5. Risk of Ruin < 1%": (risk_of_ruin < 0.01, f"Current: {risk_of_ruin*100:.2f}%"),
        "6. 6M Sharpe > Lower Bound": (rolling_6m_sharpe >= sharpe_lower_bound, f"Current 6M Sharpe: {rolling_6m_sharpe:.2f}"),
        "7. Profit Factor >= 1.0": (profit_factor >= 1.0, f"Current PF: {profit_factor:.2f}"),
        "8. Win Rate within 2 StdDev": (recent_win_rate >= (backtest_win_rate_mean - 2 * backtest_win_rate_std), f"Recent WR: {recent_win_rate*100:.1f}%"),
        "9. Live Mean >= Bootstrap CI Low": (recent_expectancy >= backtest_ci_low, f"Recent Expectancy: {recent_expectancy:.3f}R"),
        "10. Max Drawdown < Cap": (current_drawdown < max_drawdown_limit, f"Current DD: {current_drawdown*100:.2f}% (Cap: {max_drawdown_limit*100:.1f}%)"),
        "11. DD Duration < Max Months": (consecutive_dd_months < max_dd_months_limit, f"Consecutive Months in DD >5%: {consecutive_dd_months}"),
    }

    failed_critical = [name for name, (passed, _) in checks.items() if not passed and name in [
        "10. Max Drawdown < Cap", "1. Positive Expectancy", "9. Live Mean >= Bootstrap CI Low"
    ]]
    failed_warnings = [name for name, (passed, _) in checks.items() if not passed]

    if failed_critical or len(failed_warnings) >= 3:
        overall_status = "KILLED (HALT ALL TRADING IMMEDIATELY)"
    elif failed_warnings:
        overall_status = "WARNING (REDUCE POSITION SIZING / REVIEW)"
    else:
        overall_status = "ACTIVE (PASSED ALL CRITERIA)"

    return {"overall_status": overall_status, "checks": checks}


# Execution Block
if __name__ == "__main__":
    try:
        trade_df = load_and_prepare_simple_trades()
        results = calculate_metrics_and_eval_kill_criteria(trade_df)

        print("\n" + "="*65)
        print(f"STRATEGY STATUS: {results['overall_status']}")
        print("="*65)
        print(f"{'Check / Criterion':<35} | {'Status':<8} | {'Details'}")
        print("-" * 65)

        for check_name, (passed, detail) in results["checks"].items():
            status_str = "PASS" if passed else "FAIL"
            print(f"{check_name:<35} | {status_str:<8} | {detail}")

        print("-" * 65)
    finally:
        print("\nExecution completed.")