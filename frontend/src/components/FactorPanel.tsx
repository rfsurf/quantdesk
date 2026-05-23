"use client";
import { useState } from "react";
import { Search, ChevronDown, ChevronRight, GripVertical } from "lucide-react";
import clsx from "clsx";

const FACTOR_GROUPS: { category: string; factors: { key: string; label: string; description: string }[] }[] = [
  {
    category: "技术指标",
    factors: [
      { key: "ma_5", label: "MA(5)", description: "5日均线" },
      { key: "ma_10", label: "MA(10)", description: "10日均线" },
      { key: "ma_20", label: "MA(20)", description: "20日均线" },
      { key: "ma_60", label: "MA(60)", description: "60日均线" },
      { key: "ma_120", label: "MA(120)", description: "120日均线" },
      { key: "macd_dif", label: "MACD DIF", description: "快慢线差值" },
      { key: "macd_dea", label: "MACD DEA", description: "信号线" },
      { key: "rsi_7", label: "RSI(7)", description: "7日相对强弱" },
      { key: "rsi_14", label: "RSI(14)", description: "14日相对强弱" },
      { key: "bb_upper", label: "布林上轨", description: "标准差上轨" },
      { key: "bb_lower", label: "布林下轨", description: "标准差下轨" },
      { key: "atr_14", label: "ATR(14)", description: "14日平均真实波幅" },
      { key: "kdj_k", label: "KDJ-K", description: "K值" },
      { key: "kdj_d", label: "KDJ-D", description: "D值" },
      { key: "wr_14", label: "威廉指标", description: "14日威廉" },
    ],
  },
  {
    category: "成交量",
    factors: [
      { key: "volume", label: "成交量", description: "当日成交量" },
      { key: "volume_ma_5", label: "均量(5)", description: "5日均量" },
      { key: "volume_ma_20", label: "均量(20)", description: "20日均量" },
      { key: "volume_ratio", label: "量比", description: "量比" },
    ],
  },
  {
    category: "行情统计",
    factors: [
      { key: "volatility_20", label: "波动率(20)", description: "20日年化波动率" },
      { key: "momentum_20", label: "动量(20)", description: "20日收益率" },
      { key: "turnover_rate", label: "换手率", description: "换手率" },
      { key: "amplitude", label: "振幅", description: "当日振幅" },
    ],
  },
  {
    category: "条件逻辑",
    factors: [
      { key: "AND", label: "AND 同时满足", description: "所有子条件同时成立" },
      { key: "OR", label: "OR 任一满足", description: "任一子条件成立即可" },
      { key: "GOLDEN", label: "金叉", description: "快线上穿慢线" },
      { key: "DEATH", label: "死叉", description: "快线下穿慢线" },
    ],
  },
];

interface Props {
  onAddFactor: (factor: { key: string; label: string }) => void;
}

export default function FactorPanel({ onAddFactor }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ 技术指标: true });
  const [search, setSearch] = useState("");

  const toggle = (cat: string) => setExpanded((p) => ({ ...p, [cat]: !p[cat] }));

  const groups = search
    ? [{
        category: "搜索结果",
        factors: FACTOR_GROUPS.flatMap((g) =>
          g.factors.filter(
            (f) =>
              f.label.toLowerCase().includes(search.toLowerCase()) ||
              f.key.toLowerCase().includes(search.toLowerCase())
          )
        ),
      }].filter((g) => g.factors.length > 0)
    : FACTOR_GROUPS;

  return (
    <div className="factor-panel w-60 border-r border-gray-100 dark:border-navy-700/50
      bg-white/80 dark:bg-navy-800/80 backdrop-blur-sm flex flex-col h-full"
    >
      <div className="p-3 border-b border-gray-100 dark:border-navy-700/50">
        <div className="factor-panel-title text-xs font-bold text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">因子面板</div>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-200 dark:border-navy-600
              rounded-[12px] text-xs bg-white dark:bg-navy-800
              focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400 transition"
            placeholder="搜索因子..."
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {groups.map((group) => (
          <div key={group.category} className="mb-1">
            <button
              onClick={() => toggle(group.category)}
              className="flex items-center justify-between w-full px-2.5 py-2
                text-xs font-semibold text-gray-600 dark:text-gray-300
                hover:bg-gray-50 dark:hover:bg-navy-700/50 rounded-[10px] transition"
            >
              <span>{group.category}</span>
              <div className="text-gray-400 transition-transform"
                style={{ transform: expanded[group.category] !== false ? "rotate(0deg)" : "rotate(-90deg)" }}
              >
                <ChevronDown size={12} />
              </div>
            </button>
            {expanded[group.category] !== false &&
              group.factors.map((f) => (
                <button
                  key={f.key}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("application/quantdesk-factor", JSON.stringify({ key: f.key, label: f.label }));
                    e.dataTransfer.effectAllowed = "copy";
                  }}
                  onClick={() => onAddFactor({ key: f.key, label: f.label })}
                  className="w-full text-left px-2.5 py-2 text-xs text-gray-700 dark:text-gray-300
                    hover:bg-brand-50 hover:text-brand-700 dark:hover:bg-brand-900/10 dark:hover:text-brand-300
                    rounded-[10px] transition group cursor-grab active:cursor-grabbing
                    flex items-center gap-1.5"
                  title={`${f.description}（可拖拽到画布）`}
                >
                  <GripVertical size={10} className="text-gray-300 opacity-0 group-hover:opacity-100 transition" />
                  <span className="block truncate">{f.label}</span>
                </button>
              ))}
          </div>
        ))}
      </div>
      <div className="p-3 border-t border-gray-100 dark:border-navy-700/50 text-xs text-gray-400">
        <p>拖拽因子到画布，或点击添加</p>
        <p className="mt-0.5">连线组合策略逻辑</p>
      </div>
    </div>
  );
}
