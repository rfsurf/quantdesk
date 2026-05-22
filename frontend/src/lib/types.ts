// ---- Shared types matching backend schemas ----

export interface StrategyConfig {
  universe: { type: "index" | "symbols"; value: string | string[] };
  conditions: ConditionGroup;
  weights?: "equal" | "custom";
  rebalance?: { frequency: "daily" | "weekly" | "monthly" };
}

export interface ConditionGroup {
  logic: "AND" | "OR";
  children: ConditionNode[];
}

export type ConditionNode =
  | { type: "compare"; left: FactorRef; op: string; right: FactorRef; multiplier?: number }
  | { type: "cross"; fast: FactorRef; slow: FactorRef; direction: "golden" | "death" }
  | { type: "group"; logic: "AND" | "OR"; children: ConditionNode[] };

export interface FactorRef {
  factor: string;
  params?: Record<string, number>;
  value?: number;
}

export interface StrategyItem {
  id: string;
  name: string;
  status: "draft" | "saved" | "archived";
  stage: string;
  updated_at: string;
}

export interface StrategyDetail {
  id: string;
  name: string;
  status: string;
  config: StrategyConfig;
  stage: string;
  created_at: string;
  updated_at: string;
}

export interface BacktestParams {
  initial_cash?: number;
  commission_rate?: number;
  slippage_rate?: number;
  max_positions?: number;
  stop_loss_pct?: number;
  stop_profit_pct?: number;
  start_date?: string;
  end_date?: string;
}

export interface BacktestTask {
  task_id: string;
  estimated_duration_s: number;
}

export interface NavPoint {
  date: string;
  nav: number;
  daily_return: number;
  benchmark_nav: number;
}

export interface Trade {
  date: string;
  symbol: string;
  side: "buy" | "sell";
  price: number;
  volume: number;
  pnl: number;
}

export interface BacktestResult {
  backtest_id: string;
  status: "done" | "pending" | "running" | "failed";
  result?: {
    total_return: number;
    annual_return: number;
    sharpe_ratio: number;
    calmar_ratio: number;
    max_drawdown: number;
    volatility: number;
    win_rate: number;
    profit_factor: number;
    total_trades: number;
    alpha: number;
    beta: number;
    information_ratio: number;
  };
  error_message?: string;
}

export interface ScorecardResult {
  overall_score: number;
  dimensions: {
    name: string;
    score: number;
    weight: number;
    verdict: string;
  }[];
  summary: string;
}

export interface AIGenerateResult {
  session_id: string;
  config: StrategyConfig;
  summary: string;
}

export interface AIDiagnoseResult {
  scorecard: ScorecardResult;
  suggestions: string[];
}

export interface WFAResult {
  wfa_id: string;
  status: string;
  result?: {
    windows: {
      window: number;
      oos_sharpe: number;
      oos_return: number;
      passed: boolean;
    }[];
    pass_rate: number;
    avg_oos_sharpe: number;
    avg_oos_return: number;
    oos_is_ratio: number;
    robust: boolean;
  };
}

export interface FactorCategory {
  technical: string[];
  market_stat: string[];
  volume: string[];
}

// ---- Onboarding ----

export interface OnboardingTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  config: StrategyConfig;
}
