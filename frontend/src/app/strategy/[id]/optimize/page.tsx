"use client";
import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { strategyAPI, optimizeAPI } from "@/lib/api";
import {
  ArrowLeft, Zap, Target, Hash, Sliders, Play, Loader2,
  ChevronRight, CheckCircle2, TrendingUp,
} from "lucide-react";
import toast from "react-hot-toast";

interface ParamDef {
  name: string;
  label: string;
  min: number;
  max: number;
  step: number;
}

const PRESET_PARAMS: ParamDef[] = [
  { name: "ma_fast", label: "MA 快线周期", min: 1, max: 50, step: 1 },
  { name: "ma_slow", label: "MA 慢线周期", min: 5, max: 200, step: 5 },
  { name: "rsi_period", label: "RSI 周期", min: 5, max: 30, step: 1 },
  { name: "stop_loss", label: "止损比例 (%)", min: 2, max: 20, step: 1 },
];

export default function OptimizePage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const [strategyName, setStrategyName] = useState("");
  const [selectedParams, setSelectedParams] = useState<Set<string>>(new Set(["ma_fast", "ma_slow"]));
  const [ranges, setRanges] = useState<Record<string, { min: number; max: number; step: number }>>(
    Object.fromEntries(PRESET_PARAMS.map(p => [p.name, { min: p.min, max: p.max, step: p.step }]))
  );
  const [objective, setObjective] = useState("sharpe_ratio");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    strategyAPI.get(id).then(r => setStrategyName(r.data.name)).catch(() => {});
  }, [id]);

  const toggleParam = (name: string) => {
    const next = new Set(selectedParams);
    if (next.has(name)) next.delete(name); else next.add(name);
    setSelectedParams(next);
  };

  const estimatedCombos = () => {
    let total = 1;
    for (const name of selectedParams) {
      const r = ranges[name];
      if (r && r.step > 0) total *= Math.max(1, Math.floor((r.max - r.min) / r.step) + 1);
    }
    return total;
  };

  const handleRun = async () => {
    if (selectedParams.size === 0) return toast.error("请至少选择一个参数");
    setRunning(true);
    try {
      const paramRanges: any = {};
      for (const name of selectedParams) paramRanges[name] = ranges[name];
      const r = await optimizeAPI.run(id, { params: paramRanges, objective });
      setResult(r.data);
      toast.success("参数优化完成");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "优化失败，请升级到 Pro");
    }
    setRunning(false);
  };

  const combos = estimatedCombos();
  const objectiveLabels: Record<string, string> = {
    sharpe_ratio: "夏普比率",
    calmar_ratio: "卡玛比率",
    total_return: "总收益",
  };

  return (
    <div className="min-h-screen bg-lightPrimary dark:bg-navy-900">
      <Navbar />
      <main className="max-w-4xl mx-auto p-6 animate-fade-in">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <Link href={`/strategy/${id}/edit`}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 rounded-[10px] transition"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">参数优化</h1>
            <p className="text-sm text-gray-500">{strategyName || id}</p>
          </div>
        </div>

        {/* Param Selection */}
        <div className="card-glass p-6 mb-5">
          <h2 className="font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
            <Sliders size={18} className="text-brand-500" />
            选择要优化的参数
          </h2>
          <div className="space-y-3">
            {PRESET_PARAMS.map(p => (
              <div key={p.name}
                className="flex items-center gap-4 p-4 rounded-[16px] border border-gray-100 dark:border-navy-600/40
                  hover:bg-gray-50/50 dark:hover:bg-navy-700/30 transition"
              >
                <input
                  type="checkbox"
                  checked={selectedParams.has(p.name)}
                  onChange={() => toggleParam(p.name)}
                  className="w-5 h-5 rounded-lg accent-brand-600 cursor-pointer"
                />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-32">{p.label}</span>
                {selectedParams.has(p.name) && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>范围:</span>
                    <input
                      type="number" value={ranges[p.name]?.min}
                      onChange={e => setRanges(prev => ({ ...prev, [p.name]: { ...prev[p.name], min: +e.target.value } }))}
                      className="w-16 px-2 py-1.5 border border-gray-200 dark:border-navy-600 rounded-[10px] text-xs bg-white dark:bg-navy-800"
                    />
                    <span>~</span>
                    <input
                      type="number" value={ranges[p.name]?.max}
                      onChange={e => setRanges(prev => ({ ...prev, [p.name]: { ...prev[p.name], max: +e.target.value } }))}
                      className="w-16 px-2 py-1.5 border border-gray-200 dark:border-navy-600 rounded-[10px] text-xs bg-white dark:bg-navy-800"
                    />
                    <span>步长:</span>
                    <input
                      type="number" value={ranges[p.name]?.step}
                      onChange={e => setRanges(prev => ({ ...prev, [p.name]: { ...prev[p.name], step: +e.target.value } }))}
                      className="w-14 px-2 py-1.5 border border-gray-200 dark:border-navy-600 rounded-[10px] text-xs bg-white dark:bg-navy-800"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-100 dark:border-navy-600/40">
            <div>
              <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1.5">优化目标</label>
              <select
                value={objective}
                onChange={e => setObjective(e.target.value)}
                className="input-horizon px-3 py-2 text-sm cursor-pointer"
              >
                <option value="sharpe_ratio">夏普比率</option>
                <option value="calmar_ratio">卡玛比率</option>
                <option value="total_return">总收益</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-4 mt-4 p-4 bg-gray-50/80 dark:bg-navy-700/40 rounded-[14px]">
            <Hash size={16} className="text-gray-400" />
            <span className="text-sm text-gray-600 dark:text-gray-300">
              预计回测 <strong>{combos.toLocaleString()}</strong> 次
            </span>
            <span className="text-xs text-gray-400">(约 {Math.ceil(combos * 0.3)} 秒)</span>
          </div>

          <button
            onClick={handleRun}
            disabled={running || selectedParams.size === 0}
            className="flex items-center gap-2 mt-4 px-5 py-2.5 bg-brand-gradient text-white
              rounded-[16px] text-sm font-medium
              shadow-brand-glow-sm hover:shadow-brand-glow
              disabled:opacity-50 transition"
          >
            {running ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
            {running ? "优化中..." : "开始优化"}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="card-glass p-6 animate-fade-in-up">
            <h2 className="font-bold text-gray-800 dark:text-white mb-4 flex items-center gap-2">
              <Target size={18} className="text-green-500" />
              最优参数
            </h2>
            <div className="grid grid-cols-2 gap-3 mb-4">
              {result.best_params && Object.entries(result.best_params).map(([k, v]: any) => (
                <div key={k} className="p-4 bg-green-50/60 dark:bg-green-900/10 rounded-[16px]">
                  <span className="text-xs text-green-600 block mb-1">{k}</span>
                  <span className="text-lg font-bold text-green-800">{v}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <TrendingUp size={14} className="text-brand-500" />
                <span className="text-gray-500">最优 {objectiveLabels[objective]}: </span>
                <span className="font-bold text-gray-800 dark:text-white">{result.best_score?.toFixed(2)}</span>
              </div>
              <div className="flex items-center gap-2">
                <Hash size={14} className="text-gray-400" />
                <span className="text-gray-500">总组合数: </span>
                <span className="font-bold text-gray-800 dark:text-white">{result.total_combos}</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
