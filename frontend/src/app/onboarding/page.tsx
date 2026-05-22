"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { strategyAPI, defaultBacktestDates } from "@/lib/api";
import { OnboardingTemplate } from "@/lib/types";
import {
  TrendingUp,
  Activity,
  Rocket,
  Sparkles,
  ChevronRight,
  Check,
  BarChart3,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";
import toast from "react-hot-toast";

const TEMPLATES: OnboardingTemplate[] = [
  {
    id: "ma_golden_cross",
    name: "MA 金叉",
    description: "5日均线上穿20日均线时买入，经典趋势跟踪策略",
    icon: "📈",
    config: {
      universe: { type: "index", value: "000300" },
      conditions: {
        logic: "AND",
        children: [
          { type: "cross", fast: { factor: "ma_5" }, slow: { factor: "ma_20" }, direction: "golden" },
          { type: "compare", left: { factor: "volume" }, op: ">", right: { factor: "volume_ma_5" }, multiplier: 1.2 },
        ],
      },
      rebalance: { frequency: "daily" },
    },
  },
  {
    id: "mean_reversion",
    name: "均值回归",
    description: "RSI低于30超卖时买入，高于70超买时卖出",
    icon: "📊",
    config: {
      universe: { type: "index", value: "000300" },
      conditions: {
        logic: "AND",
        children: [
          { type: "compare", left: { factor: "rsi_14" }, op: "<", right: { factor: "constant", value: 30 } },
          { type: "compare", left: { factor: "volatility_20" }, op: "<", right: { factor: "constant", value: 0.03 } },
        ],
      },
      rebalance: { frequency: "daily" },
    },
  },
  {
    id: "momentum_breakout",
    name: "动量突破",
    description: "价格突破20日高点且放量时追涨，适合趋势市",
    icon: "🚀",
    config: {
      universe: { type: "index", value: "000300" },
      conditions: {
        logic: "AND",
        children: [
          { type: "compare", left: { factor: "close" }, op: ">", right: { factor: "ma_20" }, multiplier: 1.05 },
          { type: "compare", left: { factor: "volume" }, op: ">", right: { factor: "volume_ma_5" }, multiplier: 2.0 },
        ],
      },
      rebalance: { frequency: "daily" },
    },
  },
  {
    id: "macd_signal",
    name: "MACD 信号",
    description: "MACD柱状图由负转正时买入，经典动量策略",
    icon: "📉",
    config: {
      universe: { type: "index", value: "000300" },
      conditions: {
        logic: "AND",
        children: [
          { type: "compare", left: { factor: "macd_hist" }, op: ">", right: { factor: "constant", value: 0 } },
          { type: "compare", left: { factor: "macd" }, op: ">", right: { factor: "macd_signal" } },
        ],
      },
      rebalance: { frequency: "daily" },
    },
  },
  {
    id: "bollinger_bands",
    name: "布林带策略",
    description: "价格触及下轨买入，触及上轨卖出，震荡市利器",
    icon: "🎯",
    config: {
      universe: { type: "index", value: "000300" },
      conditions: {
        logic: "AND",
        children: [
          { type: "compare", left: { factor: "close" }, op: "<", right: { factor: "bb_lower" } },
          { type: "compare", left: { factor: "bb_width" }, op: ">", right: { factor: "constant", value: 0.02 } },
        ],
      },
      rebalance: { frequency: "daily" },
    },
  },
  {
    id: "kdj_oversold",
    name: "KDJ 超卖",
    description: "K值低于20时买入，适合短线反弹捕捉",
    icon: "⚡",
    config: {
      universe: { type: "index", value: "000300" },
      conditions: {
        logic: "AND",
        children: [
          { type: "compare", left: { factor: "kdj_k" }, op: "<", right: { factor: "constant", value: 20 } },
          { type: "compare", left: { factor: "kdj_d" }, op: "<", right: { factor: "kdj_k" } },
        ],
      },
      rebalance: { frequency: "daily" },
    },
  },
  {
    id: "blank",
    name: "空白画布",
    description: "从头开始搭建自己的策略",
    icon: "✨",
    config: {
      universe: { type: "index", value: "000300" },
      conditions: { logic: "AND", children: [] },
      rebalance: { frequency: "daily" },
    },
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selected, setSelected] = useState<OnboardingTemplate | null>(null);
  const [name, setName] = useState("");
  const dates = defaultBacktestDates();
  const [params, setParams] = useState({
    universe: "000300",
    startDate: dates.start_date,
    endDate: dates.end_date,
    initialCash: 100000,
  });

  useEffect(() => {
    if (!localStorage.getItem("token")) router.push("/login");
  }, [router]);

  const handleCreate = async () => {
    try {
      const r = await strategyAPI.create(
        name || selected?.name || "我的策略",
        selected?.config || TEMPLATES[3].config
      );
      toast.success("策略创建成功！");
      router.push(`/strategy/${r.data.id}/edit`);
    } catch {
      toast.error("创建失败，请重试");
    }
  };

  const stepTitles = ["", "选择模板", "配置参数", "确认创建"];
  const stepDescs = [
    "",
    "选一个模板快速开始，或从空白画布自由搭建",
    "给策略起个名字，设置回测参数",
    "确认你的策略信息，然后进入编辑器",
  ];

  return (
    <div className="min-h-screen bg-lightPrimary dark:bg-navy-900 flex items-center justify-center px-4">
      <div className="w-full max-w-2xl animate-fade-in-up">
        {/* Progress */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-10 h-10 rounded-[14px] flex items-center justify-center text-sm font-bold transition-all duration-300 ${
                  s < step
                    ? "bg-brand-gradient text-white shadow-brand-glow-sm"
                    : s === step
                    ? "bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-300 border-2 border-brand-300 dark:border-brand-700"
                    : "bg-gray-100 dark:bg-navy-700 text-gray-400 dark:text-gray-500"
                }`}
              >
                {s < step ? <Check size={16} /> : s}
              </div>
              {s < 3 && (
                <div className={`w-10 h-0.5 rounded-full transition-colors ${
                  s < step ? "bg-brand-400" : "bg-gray-200 dark:bg-navy-700"
                }`} />
              )}
            </div>
          ))}
        </div>

        {/* Title */}
        <div className="text-center mb-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">{stepTitles[step]}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{stepDescs[step]}</p>
        </div>

        {/* Step 1: Template Selection */}
        {step === 1 && (
          <div className="card-glass p-7 sm:p-8">
            <div className="grid grid-cols-2 gap-4 mb-6">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelected(t)}
                  className={`p-5 rounded-[18px] border-2 text-left transition-all duration-300 ${
                    selected?.id === t.id
                      ? "border-brand-400 bg-brand-50/80 dark:bg-brand-900/15 shadow-brand-glow-sm"
                      : "border-gray-100 dark:border-navy-600 hover:border-gray-300 dark:hover:border-navy-500 hover:-translate-y-0.5"
                  }`}
                >
                  <div className="text-3xl mb-2">{t.icon}</div>
                  <div className="font-semibold text-gray-900 dark:text-white">{t.name}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{t.description}</div>
                </button>
              ))}
            </div>
            <button
              onClick={() => {
                if (!selected) return toast.error("请先选择一个模板");
                setStep(2);
              }}
              className="w-full py-3 bg-brand-gradient text-white rounded-[16px] font-semibold
                shadow-brand-glow-sm hover:shadow-brand-glow
                hover:-translate-y-px active:translate-y-0
                transition-all duration-300 flex items-center justify-center gap-2"
            >
              下一步
              <ChevronRight size={18} />
            </button>
          </div>
        )}

        {/* Step 2: Parameters */}
        {step === 2 && (
          <div className="card-glass p-7 sm:p-8">
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">策略名称</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-horizon w-full px-4 py-2.5 text-sm"
                  placeholder={selected?.name || "我的策略"}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">股票池</label>
                  <select
                    value={params.universe}
                    onChange={(e) => setParams({ ...params, universe: e.target.value })}
                    className="input-horizon w-full px-4 py-2.5 text-sm appearance-none cursor-pointer"
                  >
                    <option value="000300">沪深300</option>
                    <option value="000905">中证500</option>
                    <option value="000852">中证1000</option>
                    <option value="399006">创业板指</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">初始资金</label>
                  <div className="relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-sm">¥</span>
                    <input
                      type="number"
                      value={params.initialCash}
                      onChange={(e) => setParams({ ...params, initialCash: Number(e.target.value) })}
                      className="input-horizon w-full pl-8 pr-4 py-2.5 text-sm"
                    />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">开始日期</label>
                  <input
                    type="date"
                    value={params.startDate}
                    onChange={(e) => setParams({ ...params, startDate: e.target.value })}
                    className="input-horizon w-full px-4 py-2.5 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">结束日期</label>
                  <input
                    type="date"
                    value={params.endDate}
                    onChange={(e) => setParams({ ...params, endDate: e.target.value })}
                    className="input-horizon w-full px-4 py-2.5 text-sm"
                  />
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-3 border border-gray-200 dark:border-navy-600
                  text-gray-700 dark:text-gray-300 rounded-[16px] font-semibold
                  hover:bg-gray-50 dark:hover:bg-navy-700/60 transition"
              >
                <div className="flex items-center justify-center gap-2">
                  <ArrowLeft size={16} />
                  上一步
                </div>
              </button>
              <button
                onClick={() => setStep(3)}
                className="flex-1 py-3 bg-brand-gradient text-white rounded-[16px] font-semibold
                  shadow-brand-glow-sm hover:shadow-brand-glow transition flex items-center justify-center gap-2"
              >
                下一步
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Confirm */}
        {step === 3 && (
          <div className="card-glass p-7 sm:p-8">
            <div className="bg-gray-50/80 dark:bg-navy-800/50 rounded-[16px] p-5 mb-6 space-y-3 text-sm">
              {[
                { label: "策略名称", value: name || selected?.name },
                { label: "模板", value: `${selected?.icon} ${selected?.name}` },
                { label: "股票池", value: params.universe },
                { label: "回测区间", value: `${params.startDate} ~ ${params.endDate}` },
                { label: "初始资金", value: `${params.initialCash.toLocaleString()} 元` },
              ].map((item) => (
                <div key={item.label} className="flex justify-between items-center py-1">
                  <span className="text-gray-500 dark:text-gray-400">{item.label}</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{item.value}</span>
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setStep(2)}
                className="flex-1 py-3 border border-gray-200 dark:border-navy-600
                  text-gray-700 dark:text-gray-300 rounded-[16px] font-semibold
                  hover:bg-gray-50 dark:hover:bg-navy-700/60 transition"
              >
                <div className="flex items-center justify-center gap-2">
                  <ArrowLeft size={16} />
                  上一步
                </div>
              </button>
              <button
                onClick={handleCreate}
                className="flex-1 py-3 bg-brand-gradient text-white rounded-[16px] font-semibold
                  shadow-brand-glow-sm hover:shadow-brand-glow transition flex items-center justify-center gap-2"
              >
                <Sparkles size={16} />
                进入策略编辑器
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
