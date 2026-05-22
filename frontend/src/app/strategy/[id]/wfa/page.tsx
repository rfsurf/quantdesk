"use client";
import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { strategyAPI, wfaAPI } from "@/lib/api";
import {
  ArrowLeft, Play, Loader2, Check, X, AlertTriangle, Info,
  BarChart3, ArrowUpRight, TrendingUp,
} from "lucide-react";
import toast from "react-hot-toast";

export default function WFAPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const [strategyName, setStrategyName] = useState("");
  const [mode, setMode] = useState<"standard" | "anchored">("standard");
  const [isWindow, setIsWindow] = useState(500);
  const [oosWindow, setOosWindow] = useState(120);
  const [step, setStep] = useState(120);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    strategyAPI.get(id).then(r => setStrategyName(r.data.name)).catch(() => {});
  }, [id]);

  const windowCount = Math.max(1, Math.floor((isWindow - oosWindow) / Math.max(step, 1)));

  const handleRun = async () => {
    setRunning(true);
    try {
      const r = await wfaAPI.run(id, { mode, is_window: isWindow, oos_window: oosWindow, step });
      setResult(r.data);
      toast.success("WFA 分析完成");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "WFA 分析失败");
    }
    setRunning(false);
  };

  const windows = result?.result?.windows || [];

  return (
    <div className="min-h-screen bg-lightPrimary dark:bg-navy-900">
      <Navbar />
      <main className="max-w-5xl mx-auto p-6 animate-fade-in">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Link href={`/strategy/${id}/edit`}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 rounded-[10px] transition"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">WFA 滚动前向分析</h1>
            <p className="text-sm text-gray-500">{strategyName || id}</p>
          </div>
        </div>

        {/* Config */}
        <div className="card-glass p-6 mb-5">
          <h2 className="font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
            <BarChart3 size={18} className="text-brand-500" />
            分析配置
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1.5">模式</label>
              <select
                value={mode}
                onChange={e => setMode(e.target.value as any)}
                className="input-horizon w-full px-3 py-2.5 text-sm cursor-pointer"
              >
                <option value="standard">Standard — 固定IS/OOS窗口，向前滚动</option>
                <option value="anchored">Anchored — 训练集逐步增长</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1.5">样本内窗口 IS (交易日)</label>
              <input type="number" value={isWindow} onChange={e => setIsWindow(+e.target.value)}
                min={252} className="input-horizon w-full px-3 py-2.5 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1.5">样本外窗口 OOS (交易日)</label>
              <input type="number" value={oosWindow} onChange={e => setOosWindow(+e.target.value)}
                min={20} className="input-horizon w-full px-3 py-2.5 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1.5">滚动步长 (交易日)</label>
              <input type="number" value={step} onChange={e => setStep(+e.target.value)}
                min={20} className="input-horizon w-full px-3 py-2.5 text-sm" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500 mb-4 p-3 bg-gray-50/80 dark:bg-navy-700/40 rounded-[14px]">
            <Info size={14} />
            预计产生 {windowCount} 个验证窗口
          </div>
          <button
            onClick={handleRun}
            disabled={running}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-gradient text-white
              rounded-[16px] text-sm font-medium shadow-brand-glow-sm hover:shadow-brand-glow
              disabled:opacity-50 transition"
          >
            {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {running ? "分析中..." : "开始 WFA 分析"}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="card-glass p-6 animate-fade-in-up">
            <h2 className="font-bold text-gray-800 dark:text-white mb-4">分析结果</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50/80 dark:bg-navy-700/40 text-gray-600 dark:text-gray-300">
                  <tr>
                    {["窗口", "OOS 收益", "OOS 夏普", "胜率", "状态"].map((h) => (
                      <th key={h} className="text-left px-3 py-2.5 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50 dark:divide-navy-700/30">
                  {windows.map((w: any, i: number) => (
                    <tr key={i} className="hover:bg-gray-50/50 dark:hover:bg-navy-700/20 transition">
                      <td className="px-3 py-3 font-medium">窗口 {w.window || i + 1}</td>
                      <td className="px-3 py-3 text-right">
                        <span className={w.oos_return > 0 ? "text-profit font-medium" : "text-loss font-medium"}>
                          {(w.oos_return * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-3 py-3 text-right">{w.oos_sharpe?.toFixed(2) || "-"}</td>
                      <td className="px-3 py-3 text-right">
                        {w.win_rate ? (w.win_rate * 100).toFixed(0) + "%" : "-"}
                      </td>
                      <td className="px-3 py-3 text-center">
                        {w.passed ? (
                          <Check size={16} className="inline text-profit" />
                        ) : (
                          <X size={16} className="inline text-loss" />
                        )}
                      </td>
                    </tr>
                  ))}
                  {windows.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-3 py-8 text-center text-gray-400">暂无窗口数据</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {result.result && (
              <div className="mt-6 p-5 bg-amber-50/80 dark:bg-amber-900/15 rounded-[18px] border border-amber-200/50">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-[10px] bg-amber-100 flex items-center justify-center shrink-0">
                    <AlertTriangle size={16} className="text-amber-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-amber-800">
                      WFA 综合评分: {result.result.wfa_score || "-"}/100
                    </p>
                    <p className="text-sm text-amber-700 mt-1">
                      {result.result.diagnosis || "分析完成，请根据各窗口表现判断策略的泛化能力。"}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
