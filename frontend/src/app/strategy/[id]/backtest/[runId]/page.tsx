"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import ReactECharts from "echarts-for-react";
import Navbar from "@/components/Navbar";
import ScoreBadge from "@/components/ScoreBadge";
import { backtestAPI, scorecardAPI, aiAPI } from "@/lib/api";
import { BacktestResult, NavPoint, Trade, ScorecardResult } from "@/lib/types";
import {
  ArrowLeft, TrendingUp, TrendingDown, BarChart3,
  Target, Zap, Shield, Bot, Loader2, Download,
  Sparkles, Activity, Percent, Hash,
} from "lucide-react";
import toast from "react-hot-toast";

export default function BacktestResultPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const runId = params.runId as string;

  const [result, setResult] = useState<BacktestResult | null>(null);
  const [navData, setNavData] = useState<NavPoint[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [scorecard, setScorecard] = useState<ScorecardResult | null>(null);
  const [diagnosis, setDiagnosis] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("token")) { router.push("/login"); return; }
    fetchData();
  }, [runId]);

  const fetchData = async () => {
    try {
      const [btR, navR, tradesR] = await Promise.all([
        backtestAPI.get(runId), backtestAPI.nav(runId), backtestAPI.trades(runId),
      ]);
      setResult(btR.data);
      setNavData(navR.data || []);
      setTrades(tradesR.data || []);
      try {
        const scR = await scorecardAPI.get(id);
        setScorecard(scR.data);
      } catch {}
    } catch { toast.error("加载回测结果失败"); }
    setLoading(false);
  };

  const handleDiagnose = async () => {
    setDiagnosing(true);
    try {
      const r = await aiAPI.diagnose(id);
      setScorecard(r.data.scorecard);
      setDiagnosis(r.data.suggestions || []);
      toast.success("策略诊断完成");
    } catch { toast.error("AI 诊断失败，请升级到 Pro"); }
    setDiagnosing(false);
  };

  const navChartOption = {
    tooltip: { trigger: "axis" as const },
    legend: { data: ["策略净值", "基准净值"], bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: 50, right: 20, top: 20, bottom: 35 },
    xAxis: {
      type: "category" as const,
      data: navData.map((p) => p.date),
      axisLabel: { formatter: (v: string) => v.slice(5), fontSize: 10, color: "#94a3b8" },
      axisLine: { lineStyle: { color: "#e2e8f0" } },
    },
    yAxis: {
      type: "value" as const,
      axisLabel: { fontSize: 10, color: "#94a3b8" },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    series: [
      {
        name: "策略净值",
        type: "line",
        data: navData.map((p) => p.nav?.toFixed(4)),
        smooth: true,
        lineStyle: { color: "#422AFB", width: 2 },
        itemStyle: { color: "#422AFB" },
        symbol: "none",
        areaStyle: {
          color: {
            type: "linear", x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(66,42,251,0.15)" },
              { offset: 1, color: "rgba(66,42,251,0.02)" },
            ],
          },
        },
      },
      {
        name: "基准净值",
        type: "line",
        data: navData.map((p) => p.benchmark_nav?.toFixed(4)),
        smooth: true,
        lineStyle: { color: "#94a3b8", width: 1.5, type: "dashed" },
        itemStyle: { color: "#94a3b8" },
        symbol: "none",
      },
    ],
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-gray-300 dark:text-gray-600" />
      </div>
    );
  }

  const perf = result?.result;

  return (
    <div className="min-h-screen bg-lightPrimary dark:bg-navy-900">
      <Navbar />
      <div className="max-w-6xl mx-auto px-6 py-6 animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/strategy/${id}/edit`)}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 rounded-[10px] transition"
            >
              <ArrowLeft size={18} />
            </button>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">回测结果</h1>
            {result?.status === "done" && (
              <span className="text-xs bg-green-50 text-profit px-2.5 py-1 rounded-full font-medium">计算完成</span>
            )}
            {result?.status === "failed" && (
              <span className="text-xs bg-red-50 text-loss px-2.5 py-1 rounded-full font-medium">{result.error_message || "回测失败"}</span>
            )}
          </div>
          {scorecard && (
            <div className="flex items-center gap-3">
              <ScoreBadge score={scorecard.overall_score} size="md" />
              <div>
                <div className="text-sm font-semibold text-gray-700 dark:text-gray-300">策略健康分</div>
                <div className="text-xs text-gray-400">满分 100</div>
              </div>
            </div>
          )}
        </div>

        {result?.status === "done" && perf && (
          <>
            {/* Performance Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
              <PerfCard label="累计收益" value={`${(perf.total_return * 100).toFixed(1)}%`}
                icon={<TrendingUp size={16} />} color={perf.total_return > 0 ? "text-profit" : "text-loss"} />
              <PerfCard label="年化收益" value={`${(perf.annual_return * 100).toFixed(1)}%`}
                icon={<Zap size={16} />} />
              <PerfCard label="最大回撤" value={`${(perf.max_drawdown * 100).toFixed(1)}%`}
                icon={<TrendingDown size={16} />} color="text-loss" />
              <PerfCard label="夏普比率" value={perf.sharpe_ratio?.toFixed(2)}
                icon={<Target size={16} />} color={perf.sharpe_ratio > 1 ? "text-profit" : "text-gray-600 dark:text-gray-300"} />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <PerfCard label="胜率" value={`${(perf.win_rate * 100).toFixed(1)}%`}
                icon={<Percent size={16} />} />
              <PerfCard label="盈亏比" value={perf.profit_factor?.toFixed(2)}
                icon={<BarChart3 size={16} />} />
              <PerfCard label="波动率" value={`${(perf.volatility * 100).toFixed(1)}%`}
                icon={<Activity size={16} />} />
              <PerfCard label="交易次数" value={String(perf.total_trades)}
                icon={<Hash size={16} />} />
            </div>

            {/* NAV Chart */}
            <div className="card-glass p-6 mb-5">
              <h3 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <BarChart3 size={18} className="text-brand-500" />
                净值曲线
              </h3>
              <ReactECharts option={navChartOption} style={{ height: 360 }} />
            </div>

            {/* Scorecard + Diagnosis */}
            {scorecard && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
                <div className="card-glass p-6">
                  <h3 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <Shield size={18} className="text-brand-500" />
                    策略健康评分
                  </h3>
                  <div className="space-y-3">
                    {scorecard.dimensions?.map((d, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <div className="flex-1 text-sm text-gray-600 dark:text-gray-300">{d.name}</div>
                        <div className="w-32 bg-gray-100 dark:bg-navy-700 rounded-full h-2">
                          <div className="h-2 rounded-full bg-brand-gradient" style={{ width: `${Math.min(d.score * 10, 100)}%` }} />
                        </div>
                        <div className="text-sm font-bold text-gray-700 dark:text-gray-300 w-8 text-right">{d.score}</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="card-glass p-6">
                  <h3 className="font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    <Bot size={18} className="text-brand-500" />
                    AI 诊断建议
                  </h3>
                  {diagnosis.length > 0 ? (
                    <ul className="space-y-2.5">
                      {diagnosis.map((s, i) => (
                        <li key={i} className="text-sm text-gray-600 dark:text-gray-300 flex items-start gap-2">
                          <div className="w-5 h-5 rounded-full bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center mt-0.5 shrink-0">
                            <Sparkles size={12} className="text-brand-500" />
                          </div>
                          {s}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-center py-6">
                      <p className="text-sm text-gray-400 mb-4">点击按钮获取 AI 诊断</p>
                      <button
                        onClick={handleDiagnose}
                        disabled={diagnosing}
                        className="flex items-center gap-2 mx-auto px-4 py-2 bg-brand-gradient text-white
                          rounded-[14px] text-sm font-medium shadow-brand-glow-sm hover:shadow-brand-glow
                          transition disabled:opacity-40"
                      >
                        {diagnosing ? <Loader2 size={16} className="animate-spin" /> : <Bot size={16} />}
                        AI 诊断
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Summary */}
            {scorecard?.summary && (
              <div className="bg-gradient-to-r from-brand-50 to-blue-50 dark:from-brand-900/20 dark:to-blue-900/20
                rounded-[20px] border border-brand-100/50 dark:border-brand-800/30 p-6 mb-5">
                <h3 className="font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                  <Sparkles size={16} className="text-brand-500" />
                  大白话总结
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">{scorecard.summary}</p>
              </div>
            )}

            {/* Trades */}
            {trades.length > 0 && (
              <div className="card-glass p-6 mb-6">
                <h3 className="font-bold text-gray-900 dark:text-white mb-4">交易记录（最近 50 笔）</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-400 text-xs border-b border-gray-100 dark:border-navy-600/50">
                        {["日期", "标的", "方向", "价格", "数量", "盈亏"].map((h) => (
                          <th key={h} className="pb-2 pr-4 font-medium">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {trades.slice(0, 50).map((t, i) => (
                        <tr key={i} className="border-b border-gray-50 dark:border-navy-600/30 hover:bg-gray-50/50 dark:hover:bg-navy-700/20 transition">
                          <td className="py-2 pr-4">{t.date}</td>
                          <td className="py-2 pr-4 font-mono text-xs">{t.symbol}</td>
                          <td className="py-2 pr-4">
                            <span className={`text-xs px-2 py-0.5 rounded-[6px] font-medium ${
                              t.side === "buy" ? "bg-green-50 text-profit" : "bg-red-50 text-loss"
                            }`}>
                              {t.side === "buy" ? "买入" : "卖出"}
                            </span>
                          </td>
                          <td className="py-2 pr-4">{t.price?.toFixed(2)}</td>
                          <td className="py-2 pr-4">{t.volume}</td>
                          <td className={`py-2 font-medium ${t.pnl > 0 ? "text-profit" : "text-loss"}`}>
                            {t.pnl ? t.pnl.toFixed(2) : "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Export */}
            <div className="text-center pb-8">
              <button
                onClick={() => {
                  const html = generateReportHTML({
                    strategyName: "回测策略", runId,
                    result: perf, scorecard, diagnosis, trades: trades.slice(0, 50),
                  });
                  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `backtest-report-${runId.slice(0, 8)}.html`;
                  a.click();
                  URL.revokeObjectURL(url);
                  toast.success("报告已下载");
                }}
                className="inline-flex items-center gap-2 px-4 py-2
                  border border-gray-200 dark:border-navy-600
                  text-gray-600 dark:text-gray-300 rounded-[14px] text-sm
                  hover:bg-gray-50 dark:hover:bg-navy-700/50 transition"
              >
                <Download size={14} />
                导出回测报告
              </button>
            </div>
          </>
        )}

        {result?.status === "failed" && (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-[16px] bg-red-50 flex items-center justify-center mx-auto mb-4">
              <TrendingDown size={28} className="text-loss" />
            </div>
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">回测执行失败</h3>
            <p className="text-sm text-gray-500">{result.error_message}</p>
            <button
              onClick={() => router.push(`/strategy/${id}/edit`)}
              className="mt-5 inline-flex items-center gap-2 px-4 py-2 bg-brand-gradient text-white
                rounded-[14px] text-sm font-medium shadow-brand-glow-sm transition"
            >
              <ArrowLeft size={14} />
              返回编辑器
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function PerfCard({ label, value, icon, color = "text-gray-600 dark:text-gray-300" }: {
  label: string; value: string; icon: React.ReactNode; color?: string;
}) {
  return (
    <div className="card-horizon p-4 hover:-translate-y-0.5 transition-all duration-300">
      <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
        {icon}
        {label}
      </div>
      <div className={`text-xl font-bold ${color}`}>{value}</div>
    </div>
  );
}

function generateReportHTML({ strategyName, runId, result, scorecard, diagnosis, trades }: {
  strategyName: string; runId: string; result: any; scorecard: any; diagnosis: string[]; trades: any[];
}) {
  const formatPct = (v: number) => `${(v * 100).toFixed(2)}%`;
  const metrics = [
    ["累计收益", formatPct(result?.total_return || 0)],
    ["年化收益", formatPct(result?.annual_return || 0)],
    ["夏普比率", result?.sharpe_ratio?.toFixed(2) || "-"],
    ["卡玛比率", result?.calmar_ratio?.toFixed(2) || "-"],
    ["最大回撤", formatPct(result?.max_drawdown || 0)],
    ["波动率", formatPct(result?.volatility || 0)],
    ["胜率", formatPct(result?.win_rate || 0)],
    ["盈亏比", result?.profit_factor?.toFixed(2) || "-"],
    ["交易次数", String(result?.total_trades || 0)],
    ["Alpha", result?.alpha?.toFixed(4) || "-"],
    ["Beta", result?.beta?.toFixed(2) || "-"],
    ["信息比率", result?.information_ratio?.toFixed(2) || "-"],
  ];
  const tradesRows = trades.map((t) => `...`).join("");
  return `<!DOCTYPE html>...`;
}
