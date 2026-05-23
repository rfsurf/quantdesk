"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import FactorPanel from "@/components/FactorPanel";
import StrategyCanvas from "@/components/StrategyCanvas";
import GuidedTour from "@/components/GuidedTour";
import { strategyAPI, backtestAPI, qmtAPI, defaultBacktestDates } from "@/lib/api";
import { StrategyDetail, StrategyConfig } from "@/lib/types";
import {
  ArrowLeft, Save, Play, Download, Loader2, History, ChevronRight,
  Sparkles, Sliders, BarChart3, X,
} from "lucide-react";
import toast from "react-hot-toast";

const DEFAULT_CONFIG: StrategyConfig = {
  universe: { type: "index", value: "000300" },
  conditions: { logic: "AND", children: [] },
  rebalance: { frequency: "daily" },
};

export default function StrategyEditorPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  const isNew = id === "new";

  const [strategy, setStrategy] = useState<StrategyDetail | null>(null);
  const [name, setName] = useState("");
  const [config, setConfig] = useState<StrategyConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const dates = defaultBacktestDates();
  const [backtestParams, setBacktestParams] = useState({
    initial_cash: 100000,
    commission_rate: 0.0003,
    slippage_rate: 0.0001,
    max_positions: 10,
    stop_loss_pct: "",
    stop_profit_pct: "",
    ...dates,
    rebalance: "daily",
  });
  const [versions, setVersions] = useState<any[]>([]);
  const [showVersions, setShowVersions] = useState(false);

  useEffect(() => {
    if (!loading && !localStorage.getItem("qd_tour_editor") && isNew) {
      setShowTour(true);
    }
  }, [loading, isNew]);

  useEffect(() => {
    if (!localStorage.getItem("token")) { router.push("/login"); return; }
    if (isNew) { setLoading(false); return; }
    fetchStrategy();
    fetchVersions();
  }, [id]);

  const fetchStrategy = async () => {
    try {
      const r = await strategyAPI.get(id);
      setStrategy(r.data);
      setName(r.data.name);
      setConfig(r.data.config || DEFAULT_CONFIG);
    } catch { toast.error("策略不存在"); router.push("/dashboard"); }
    setLoading(false);
  };

  const fetchVersions = async () => {
    try {
      const r = await strategyAPI.versions(id);
      setVersions(r.data || []);
    } catch {}
  };

  const handleSave = async () => {
    if (!name.trim()) return toast.error("请输入策略名称");
    setSaving(true);
    try {
      if (isNew) {
        const r = await strategyAPI.create(name, config);
        toast.success("策略已创建");
        router.replace(`/strategy/${r.data.id}/edit`);
      } else {
        await strategyAPI.update(id, { name, config });
        toast.success("已保存");
        fetchVersions();
      }
    } catch { toast.error("保存失败"); }
    setSaving(false);
  };

  const handleBacktest = async () => {
    const sid = isNew ? null : id;
    if (!sid) { toast.error("请先保存策略"); return; }
    setRunning(true);
    try {
      const r = await backtestAPI.run(sid, {
        ...backtestParams,
        stop_loss_pct: backtestParams.stop_loss_pct ? Number(backtestParams.stop_loss_pct) : undefined,
        stop_profit_pct: backtestParams.stop_profit_pct ? Number(backtestParams.stop_profit_pct) : undefined,
      });
      toast.success("回测完成");
      router.push(`/strategy/${sid}/backtest/${r.data.task_id}`);
    } catch { toast.error("回测失败"); }
    setRunning(false);
  };

  const handleExport = async () => {
    if (isNew) { toast.error("请先保存策略"); return; }
    try {
      const r = await qmtAPI.exportScript(id);
      const blob = new Blob([r.data], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name || "strategy"}.py`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("QMT 脚本已下载");
    } catch { toast.error("导出失败"); }
  };

  const handleAddFactor = useCallback((factor: { key: string; label: string }) => {
    if (["AND", "OR"].includes(factor.key)) {
      setConfig(prev => ({
        ...prev,
        conditions: { ...prev.conditions, logic: factor.key as "AND" | "OR" },
      }));
      toast.success(`条件逻辑改为: ${factor.key}`);
      return;
    }
    if (factor.key === "GOLDEN" || factor.key === "DEATH") {
      const newCond: any = {
        type: "cross",
        fast: { factor: "ma_5" }, slow: { factor: "ma_20" },
        direction: factor.key === "GOLDEN" ? "golden" : "death",
      };
      setConfig(prev => ({
        ...prev,
        conditions: { ...prev.conditions, children: [...prev.conditions.children, newCond] },
      }));
      toast.success(`已添加: ${factor.label}`);
      return;
    }
    const newCond: any = {
      type: "compare",
      left: { factor: factor.key }, op: ">", right: { factor: "constant", value: 0 },
    };
    setConfig(prev => ({
      ...prev,
      conditions: { ...prev.conditions, children: [...prev.conditions.children, newCond] },
    }));
    toast.success(`已添加: ${factor.label}`);
  }, []);

  const removeCondition = (index: number) => {
    setConfig(prev => ({
      ...prev,
      conditions: { ...prev.conditions, children: prev.conditions.children.filter((_: any, i: number) => i !== index) },
    }));
  };

  const handleDropFactor = useCallback((factor: { key: string; label: string }, _position: { x: number; y: number }) => {
    handleAddFactor(factor);
  }, [handleAddFactor]);

  const updateCondition = (index: number, updated: any) => {
    setConfig(prev => ({
      ...prev,
      conditions: {
        ...prev.conditions,
        children: prev.conditions.children.map((c: any, i: number) => i === index ? { ...c, ...updated } : c),
      },
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-gray-300 dark:text-gray-600" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      <Navbar />

      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2.5
        border-b border-gray-100 dark:border-navy-700/50
        bg-white/80 dark:bg-navy-800/80 backdrop-blur-sm"
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dashboard")}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 rounded-[10px] transition"
          >
            <ArrowLeft size={18} />
          </button>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="text-lg font-bold text-gray-900 dark:text-white
              bg-transparent border-b border-transparent hover:border-gray-300 focus:border-brand-400 focus:outline-none px-1
              transition-colors"
            placeholder="策略名称"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setShowVersions(!showVersions)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400
              hover:bg-gray-100 dark:hover:bg-navy-700/50 rounded-[12px] transition"
          >
            <History size={14} />
            版本 ({versions.length + 1})
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300
              border border-gray-200 dark:border-navy-600 rounded-[12px]
              hover:bg-gray-50 dark:hover:bg-navy-700/50 transition"
          >
            <Download size={14} />
            导出QMT
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm text-white
              bg-brand-gradient rounded-[12px]
              shadow-brand-glow-sm hover:shadow-brand-glow transition disabled:opacity-40"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            保存
          </button>
        </div>
      </div>

      {/* Main editor area */}
      <div className="flex flex-1 overflow-hidden bg-lightPrimary dark:bg-navy-900">
        <FactorPanel onAddFactor={handleAddFactor} />

        <div className="flex-1 flex flex-col">
          <StrategyCanvas config={config} onChange={setConfig} onDropFactor={handleDropFactor} />

          {/* Conditions list */}
          {config.conditions.children.length > 0 && (
            <div className="h-44 border-t border-gray-100 dark:border-navy-700/50 bg-white/80 dark:bg-navy-800/80 overflow-y-auto p-3">
              <div className="text-xs font-bold text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-1.5">
                <Sliders size={12} />
                条件列表（逻辑: {config.conditions.logic}）
              </div>
              {config.conditions.children.map((c: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center gap-2 mb-1.5 text-xs bg-gray-50 dark:bg-navy-700/50 rounded-[10px] px-3 py-1.5"
                >
                  <span className="text-gray-400 w-5 font-mono">#{i + 1}</span>
                  {c.type === "compare" ? (
                    <>
                      <select
                        value={c.left?.factor || ""}
                        onChange={(e) => updateCondition(i, { left: { ...c.left, factor: e.target.value } })}
                        className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-[8px] px-2 py-1 text-xs cursor-pointer"
                      >
                        <option value="">选因子</option>
                        <option value="ma_5">MA(5)</option>
                        <option value="ma_10">MA(10)</option>
                        <option value="ma_20">MA(20)</option>
                        <option value="rsi_14">RSI(14)</option>
                        <option value="volume">成交量</option>
                        <option value="close">收盘价</option>
                        <option value="volatility_20">波动率</option>
                      </select>
                      <select
                        value={c.op || ">"}
                        onChange={(e) => updateCondition(i, { op: e.target.value })}
                        className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-[8px] px-2 py-1 text-xs cursor-pointer"
                      >
                        <option value=">">大于</option>
                        <option value="<">小于</option>
                        <option value=">=">大于等于</option>
                        <option value="<=">小于等于</option>
                      </select>
                      {c.right?.factor === "constant" ? (
                        <input
                          type="number"
                          value={c.right?.value || 0}
                          onChange={(e) => updateCondition(i, { right: { ...c.right, value: Number(e.target.value) } })}
                          className="w-24 bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-[8px] px-2 py-1 text-xs"
                          step="0.01"
                        />
                      ) : (
                        <select
                          value={c.right?.factor || ""}
                          onChange={(e) => updateCondition(i, {
                            right: e.target.value ? { factor: e.target.value } : { factor: "constant", value: 0 },
                          })}
                          className="bg-white dark:bg-navy-800 border border-gray-200 dark:border-navy-600 rounded-[8px] px-2 py-1 text-xs cursor-pointer"
                        >
                          <option value="">选因子</option>
                          <option value="constant">固定值</option>
                          <option value="ma_5">MA(5)</option>
                          <option value="ma_20">MA(20)</option>
                          <option value="volume_ma_5">均量(5)</option>
                          <option value="rsi_14">RSI(14)</option>
                        </select>
                      )}
                    </>
                  ) : c.type === "cross" ? (
                    <span className="text-gray-600 dark:text-gray-300">
                      {c.fast?.factor || "?"} {c.direction === "golden" ? "金叉" : "死叉"} {c.slow?.factor || "?"}
                    </span>
                  ) : (
                    <span className="text-gray-500">复杂条件</span>
                  )}
                  <button
                    onClick={() => removeCondition(i)}
                    className="ml-auto p-1 text-gray-300 hover:text-loss rounded-[6px] hover:bg-red-50 dark:hover:bg-red-900/20 transition"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-gray-100 dark:border-navy-700/50 bg-white/80 dark:bg-navy-800/80
        backdrop-blur-sm px-4 py-2.5 flex items-center gap-3 flex-wrap"
      >
        {[
          { label: "初始资金", key: "initial_cash", type: "number", step: 1 },
          { label: "费率", key: "commission_rate", type: "number", step: 0.0001 },
          { label: "滑点", key: "slippage_rate", type: "number", step: 0.0001 },
          { label: "持仓上限", key: "max_positions", type: "number", step: 1 },
          { label: "止损%", key: "stop_loss_pct", type: "text", placeholder: "可选" },
          { label: "止盈%", key: "stop_profit_pct", type: "text", placeholder: "可选" },
        ].map((field) => (
          <div key={field.key} className="flex items-center gap-2">
            <label className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">{field.label}</label>
            <input
              type={field.type}
              value={(backtestParams as any)[field.key]}
              onChange={(e) => setBacktestParams({ ...backtestParams, [field.key]: field.type === "number" ? Number(e.target.value) : e.target.value })}
              className="w-24 px-2 py-1.5 border border-gray-200 dark:border-navy-600 rounded-[10px] text-xs
                bg-white dark:bg-navy-800 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
              step={field.step}
              placeholder={(field as any).placeholder}
            />
          </div>
        ))}
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">调仓</label>
          <select
            value={backtestParams.rebalance}
            onChange={(e) => setBacktestParams({ ...backtestParams, rebalance: e.target.value })}
            className="px-2 py-1.5 border border-gray-200 dark:border-navy-600 rounded-[10px] text-xs bg-white dark:bg-navy-800 cursor-pointer"
          >
            <option value="daily">每日</option>
            <option value="weekly">每周</option>
            <option value="monthly">每月</option>
          </select>
        </div>
        <button
          onClick={handleBacktest}
          disabled={running}
          className="flex items-center gap-1.5 px-5 py-1.5 bg-profit text-white rounded-[12px] text-sm font-semibold
            hover:shadow-card disabled:opacity-40 transition ml-auto"
        >
          {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          开始回测
        </button>
        {!isNew && (
          <>
            <Link href={`/strategy/${id}/wfa`}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300
                hover:bg-gray-100 dark:hover:bg-navy-700/50 rounded-[12px] transition"
            >
              WFA
            </Link>
            <Link href={`/strategy/${id}/optimize`}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300
                hover:bg-gray-100 dark:hover:bg-navy-700/50 rounded-[12px] transition"
            >
              优化
            </Link>
          </>
        )}
      </div>

      {/* Version history modal */}
      {showVersions && (
        <div className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center p-4"
          onClick={() => setShowVersions(false)}
        >
          <div className="bg-white dark:bg-navy-700 rounded-[20px] shadow-elevated dark:shadow-elevated-dark p-6 w-96 max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-900 dark:text-white">策略版本历史</h3>
              <button
                onClick={() => setShowVersions(false)}
                className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-[10px] transition"
              >
                <X size={16} />
              </button>
            </div>
            {versions.length === 0 ? (
              <p className="text-sm text-gray-400">暂无历史版本</p>
            ) : (
              <div className="space-y-2">
                {versions.map((v: any, i: number) => (
                  <div key={i} className="text-sm bg-gray-50 dark:bg-navy-800/50 rounded-[14px] p-3">
                    <div className="font-semibold text-gray-700 dark:text-gray-300">版本 {v.version}</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {new Date(v.created_at).toLocaleString("zh-CN")}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tour */}
      {showTour && (
        <GuidedTour
          storageKey="qd_tour_editor"
          steps={[
            {
              selector: "input[placeholder='策略名称']",
              title: "给策略起个名字",
              content: "好的名字让你一眼就知道这个策略是做什么的。",
              action: "输入策略名称",
            },
            {
              selector: ".factor-panel-title",
              title: "因子面板",
              content: "左侧是因子库，包含技术指标、行情统计等因子。拖拽因子到画布上开始搭建策略。",
              action: "浏览可用的因子",
            },
            {
              selector: "button:has([data-lucine='play'])",
              title: "配置回测参数",
              content: "底部工具栏可以设置初始资金、费率、止损止盈等参数。",
              action: "调整参数后点击「开始回测」",
            },
            {
              selector: "button:has([data-lucine='save'])",
              title: "保存策略",
              content: "随时保存你的策略，每次保存都会生成版本历史，方便回退。",
              action: "点击保存按钮",
            },
          ]}
          onComplete={() => setShowTour(false)}
        />
      )}
    </div>
  );
}
