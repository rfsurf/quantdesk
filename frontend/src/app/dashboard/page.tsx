"use client";
import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import GuidedTour from "@/components/GuidedTour";
import { strategyAPI, backtestAPI, aiAPI, userAPI, authAPI, defaultBacktestDates } from "@/lib/api";
import { StrategyItem } from "@/lib/types";
import { useAuthStore } from "@/store";
import {
  PlusCircle,
  Play,
  Trash2,
  Edit3,
  Clock,
  Bot,
  Loader2,
  Key,
  Zap,
  Eye,
  EyeOff,
  BarChart3,
  CheckCircle,
  XCircle,
  RefreshCw,
  ArrowUpRight,
  Sparkles,
  Settings,
  Save,
  Wand2,
  Lock,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">
      <Loader2 size={32} className="animate-spin text-gray-300 dark:text-gray-600" />
    </div>}>
      <DashboardContent />
    </Suspense>
  );
}

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") || "strategies";
  const { user, setAuth } = useAuthStore();

  const [strategies, setStrategies] = useState<StrategyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [showTour, setShowTour] = useState(false);
  const [aiSettings, setAiSettings] = useState<any>(null);
  const [byokKey, setByokKey] = useState("");
  const [byokProvider, setByokProvider] = useState("deepseek");
  const [showKey, setShowKey] = useState(false);
  const [savingKey, setSavingKey] = useState(false);
  const [backtestHistory, setBacktestHistory] = useState<any[]>([]);
  const [backtestsLoading, setBacktestsLoading] = useState(false);
  const [changePassword, setChangePassword] = useState({ old: "", new: "" });
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    // 只在策略列表Tab（默认Tab）显示引导，避免遮挡其他Tab内容
    if (!loading && activeTab === "strategies" && !localStorage.getItem("qd_tour_dashboard")) {
      setShowTour(true);
    }
  }, [loading, activeTab]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    if (!user) {
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        setAuth(token, { id: payload.sub, email: payload.email || "" });
      } catch {}
    }
    fetchStrategies();
  }, []);

  useEffect(() => {
    if (activeTab === "settings" || activeTab === "ai") {
      userAPI.getAISettings().then(r => {
        setAiSettings(r.data);
        if (r.data.has_api_key) setByokKey("••••••••");
      }).catch(() => {});
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeTab === "backtests") fetchBacktestHistory();
  }, [activeTab]);

  const fetchStrategies = async () => {
    try {
      const r = await strategyAPI.list();
      setStrategies(r.data.items || []);
    } catch {
      toast.error("加载策略列表失败");
    }
    setLoading(false);
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确定删除策略"${name}"？此操作不可撤销。`)) return;
    try {
      await strategyAPI.delete(id);
      setStrategies((prev) => prev.filter((s) => s.id !== id));
      toast.success("已删除");
    } catch {
      toast.error("删除失败");
    }
  };

  const handleBacktest = async (id: string) => {
    try {
      const r = await backtestAPI.run(id, {
        initial_cash: 100000,
        commission_rate: 0.0003,
        slippage_rate: 0.0001,
        ...defaultBacktestDates(),
      });
      toast.success("回测已启动");
      router.push(`/strategy/${id}/backtest/${r.data.task_id}`);
    } catch {
      toast.error("回测启动失败");
    }
  };

  const fetchBacktestHistory = async () => {
    setBacktestsLoading(true);
    try {
      const r = await backtestAPI.list();
      setBacktestHistory(r.data.items || []);
    } catch {}
    setBacktestsLoading(false);
  };

  const handleAIGenerate = async () => {
    if (!aiPrompt.trim()) return toast.error("请输入你的策略想法");
    setAiGenerating(true);
    try {
      const r = await aiAPI.generate(aiPrompt);
      const createR = await strategyAPI.create(
        "AI生成: " + aiPrompt.slice(0, 20),
        r.data.config
      );
      toast.success("AI 策略已生成！");
      router.push(`/strategy/${createR.data.id}/edit`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "AI 生成失败，请升级到 Pro");
    }
    setAiGenerating(false);
  };

  const renderTab = () => {
    switch (activeTab) {
      case "ai":
        return (
          <div className="max-w-2xl mx-auto animate-fade-in">
            <div className="card-glass p-8">
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-blue-500 rounded-[14px]
                  flex items-center justify-center text-white shadow-brand-glow-sm"
                >
                  <Bot size={22} />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white">AI 策略助手</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">用自然语言描述你的交易想法</p>
                </div>
              </div>

              <div className="relative">
                <textarea
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  rows={4}
                  className="input-horizon w-full px-4 py-3 text-sm resize-none"
                  placeholder='比如："帮我做一个震荡市低吸高抛策略，当RSI低于30且成交量放大时买入"'
                />
                <div className="absolute bottom-3 right-3">
                  <span className="text-xs text-gray-400">{aiPrompt.length}/500</span>
                </div>
              </div>

              <div className="flex items-center gap-3 mt-5">
                <button
                  onClick={handleAIGenerate}
                  disabled={aiGenerating || !aiPrompt.trim()}
                  className="flex items-center gap-2 px-5 py-2.5 bg-brand-gradient text-white
                    rounded-[16px] font-medium text-sm
                    shadow-brand-glow-sm hover:shadow-brand-glow
                    hover:-translate-y-px active:translate-y-0
                    disabled:opacity-40 transition-all duration-300"
                >
                  {aiGenerating ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Wand2 size={16} />
                  )}
                  {aiGenerating ? "生成中..." : "生成策略"}
                </button>
                <div className="flex items-center gap-2">
                  {aiSettings ? (
                    <>
                      <span className={clsx(
                        "text-xs px-2.5 py-1 rounded-[10px] font-medium",
                        aiSettings.plan === "pro"
                          ? "bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400"
                          : "bg-gray-100 dark:bg-navy-700 text-gray-500 dark:text-gray-400"
                      )}>
                        {aiSettings.plan.toUpperCase()}
                      </span>
                      {aiSettings.has_api_key && (
                        <span className="text-xs bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 px-2 py-1 rounded-[10px] font-medium">自带Key</span>
                      )}
                      {aiSettings.ai_calls_limit > 0 && (
                        <span className="text-xs text-gray-400">{aiSettings.ai_calls_used}/{aiSettings.ai_calls_limit}</span>
                      )}
                    </>
                  ) : (
                    <span className="text-xs text-gray-400">Pro 功能</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        );

      case "backtests":
        return (
          <div className="animate-fade-in">
            <div className="flex items-center justify-between mb-5">
              <h2 className="section-title">回测记录</h2>
              <button
                onClick={fetchBacktestHistory}
                className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400
                  hover:text-brand-500 transition px-3 py-1.5 rounded-[12px] hover:bg-gray-50 dark:hover:bg-navy-700/50"
              >
                <RefreshCw size={14} className={backtestsLoading ? "animate-spin" : ""} />
                刷新
              </button>
            </div>
            {backtestsLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 size={32} className="animate-spin text-gray-300 dark:text-gray-600" />
              </div>
            ) : backtestHistory.length === 0 ? (
              <div className="text-center py-20 card-glass">
                <div className="w-16 h-16 rounded-[14px] bg-gray-50 dark:bg-navy-700/50
                  flex items-center justify-center mx-auto mb-4"
                >
                  <BarChart3 size={32} className="text-gray-300 dark:text-gray-600" />
                </div>
                <p className="text-gray-500 dark:text-gray-400 font-medium">暂无回测记录</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">创建策略并运行回测后，结果将显示在这里</p>
              </div>
            ) : (
              <div className="space-y-3">
                {backtestHistory.map((bt: any) => (
                  <div
                    key={bt.id}
                    className="card-horizon p-4 cursor-pointer hover:-translate-y-0.5 transition-all duration-300"
                    onClick={() => {
                      if (bt.status === "done") {
                        router.push(`/strategy/${bt.strategy_id}/backtest/${bt.id}`);
                      }
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-[12px] flex items-center justify-center ${
                          bt.status === "done" ? "bg-green-50 dark:bg-green-900/20" :
                          bt.status === "failed" ? "bg-red-50 dark:bg-red-900/20" :
                          "bg-gray-50 dark:bg-navy-700/50"
                        }`}>
                          {bt.status === "done" ? (
                            <CheckCircle size={18} className="text-profit" />
                          ) : bt.status === "failed" ? (
                            <XCircle size={18} className="text-loss" />
                          ) : (
                            <RefreshCw size={18} className="text-gray-400 animate-spin" />
                          )}
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900 dark:text-white text-sm">{bt.strategy_name}</h3>
                          <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                            <Clock size={11} />
                            {bt.created_at ? new Date(bt.created_at).toLocaleString("zh-CN") : "-"}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {bt.status === "done" && bt.result && (
                          <div className="text-right">
                            <div className={`text-sm font-bold ${(bt.result.total_return || 0) > 0 ? "text-profit" : "text-loss"}`}>
                              {((bt.result.total_return || 0) * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-gray-400">夏普 {(bt.result.sharpe_ratio || 0).toFixed(2)}</div>
                          </div>
                        )}
                        <span className={clsx(
                          "text-xs px-2.5 py-1 rounded-full font-medium",
                          bt.status === "done" ? "bg-green-50 dark:bg-green-900/20 text-profit" :
                          bt.status === "failed" ? "bg-red-50 dark:bg-red-900/20 text-loss" :
                          "bg-gray-50 dark:bg-navy-700 text-gray-500 dark:text-gray-400"
                        )}>
                          {bt.status === "done" ? "完成" :
                           bt.status === "failed" ? "失败" :
                           bt.status === "running" ? "运行中" : "等待中"}
                        </span>
                      </div>
                    </div>
                    {bt.status === "failed" && bt.error_message && (
                      <p className="text-xs text-red-400 mt-2 truncate">{bt.error_message}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "settings":
        return (
          <div className="max-w-xl space-y-5 animate-fade-in">
            {/* Account */}
            <div className="card-glass p-6">
              <h2 className="section-title mb-4">账户设置</h2>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between py-2.5 border-b border-gray-100 dark:border-navy-600/50">
                  <span className="text-gray-500 dark:text-gray-400">邮箱</span>
                  <span className="font-medium">{user?.email || "-"}</span>
                </div>
                <div className="flex justify-between py-2.5 border-b border-gray-100 dark:border-navy-600/50">
                  <span className="text-gray-500 dark:text-gray-400">版本</span>
                  <span className="font-medium">v2.0</span>
                </div>
              </div>
            </div>

            {/* Change Password */}
            <div className="card-glass p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-[10px] bg-red-50 dark:bg-red-900/20 flex items-center justify-center">
                  <Lock size={14} className="text-red-500" />
                </div>
                <h3 className="font-bold text-gray-900 dark:text-white">修改密码</h3>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1.5">原密码</label>
                  <input
                    type="password"
                    value={changePassword.old}
                    onChange={(e) => setChangePassword(prev => ({ ...prev, old: e.target.value }))}
                    className="input-horizon w-full px-3 py-2 text-sm"
                    placeholder="输入原密码"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1.5">新密码</label>
                  <input
                    type="password"
                    value={changePassword.new}
                    onChange={(e) => setChangePassword(prev => ({ ...prev, new: e.target.value }))}
                    className="input-horizon w-full px-3 py-2 text-sm"
                    placeholder="输入新密码（至少8位）"
                  />
                </div>
                <button
                  onClick={async () => {
                    if (!changePassword.old || !changePassword.new) {
                      toast.error("请填写完整");
                      return;
                    }
                    if (changePassword.new.length < 8) {
                      toast.error("新密码至少8位");
                      return;
                    }
                    setChangingPassword(true);
                    try {
                      await authAPI.changePassword(changePassword.old, changePassword.new);
                      setChangePassword({ old: "", new: "" });
                      toast.success("密码已更新");
                    } catch (err: any) {
                      toast.error(err.response?.data?.detail || "修改失败");
                    }
                    setChangingPassword(false);
                  }}
                  disabled={changingPassword}
                  className="px-4 py-2 bg-brand-gradient text-white rounded-[14px] text-sm font-medium
                    shadow-brand-glow-sm hover:shadow-brand-glow transition flex items-center gap-2"
                >
                  {changingPassword ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  {changingPassword ? "修改中..." : "修改密码"}
                </button>
              </div>
            </div>

            {/* Plan */}
            <div className="card-glass p-6">
              <h3 className="font-bold text-gray-900 dark:text-white mb-4">套餐与 AI 额度</h3>
              {aiSettings ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={clsx(
                        "text-xs px-2.5 py-1 rounded-[10px] font-semibold",
                        aiSettings.plan === "pro"
                          ? "bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400"
                          : "bg-gray-100 dark:bg-navy-700 text-gray-600 dark:text-gray-300"
                      )}>
                        {aiSettings.plan.toUpperCase()}
                      </span>
                      {aiSettings.has_api_key && (
                        <span className="text-xs bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 px-2 py-1 rounded-[10px] font-medium">自带Key</span>
                      )}
                    </div>
                    {aiSettings.ai_calls_limit > 0 && (
                      <span className="text-xs text-gray-400">已用 {aiSettings.ai_calls_used} / {aiSettings.ai_calls_limit} 次</span>
                    )}
                    {aiSettings.ai_calls_limit === -1 && (
                      <span className="text-xs text-green-600 font-medium">不限次数</span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {aiSettings.plan !== "pro" && (
                      <button
                        onClick={async () => {
                          await userAPI.upgrade("pro");
                          const r = await userAPI.getAISettings();
                          setAiSettings(r.data);
                          toast.success("已升级到 Pro！");
                        }}
                        className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 text-white
                          rounded-[14px] text-sm font-medium hover:bg-amber-600 transition"
                      >
                        <Zap size={14} />
                        升级 Pro（500次/月）
                      </button>
                    )}
                    {aiSettings.plan === "pro" && (
                      <button
                        onClick={async () => {
                          await userAPI.upgrade("free");
                          const r = await userAPI.getAISettings();
                          setAiSettings(r.data);
                          toast.success("已切换至 Free");
                        }}
                        className="px-4 py-2 border border-gray-200 dark:border-navy-600
                          text-gray-600 dark:text-gray-300 rounded-[14px] text-sm
                          hover:bg-gray-50 dark:hover:bg-navy-700/50 transition"
                      >
                        切换至 Free
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex items-center py-4">
                  <Loader2 size={18} className="animate-spin text-gray-300" />
                </div>
              )}
            </div>

            {/* BYOK */}
            <div className="card-glass p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-[10px] bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center">
                  <Key size={14} className="text-brand-500" />
                </div>
                <h3 className="font-bold text-gray-900 dark:text-white">自带 API Key（BYOK）</h3>
              </div>
              <p className="text-xs text-gray-500 mb-4">
                使用你自己的 DeepSeek API Key 或本地 Ollama，不占用平台额度，不限调用次数。
              </p>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1.5">API Key</label>
                  <div className="flex gap-2">
                    <input
                      type={showKey ? "text" : "password"}
                      value={byokKey}
                      onChange={(e) => setByokKey(e.target.value)}
                      placeholder="sk-..."
                      className="input-horizon flex-1 px-3 py-2 text-sm"
                    />
                    <button
                      onClick={() => setShowKey(!showKey)}
                      className="p-2 rounded-[12px] text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition"
                    >
                      {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1.5">提供商</label>
                  <select
                    value={byokProvider}
                    onChange={(e) => setByokProvider(e.target.value)}
                    className="input-horizon w-full px-3 py-2 text-sm cursor-pointer"
                  >
                    <option value="deepseek">DeepSeek API</option>
                    <option value="ollama">Ollama（本地）</option>
                  </select>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={async () => {
                      setSavingKey(true);
                      try {
                        await userAPI.updateAISettings({
                          ai_api_key: byokKey === "••••••••" ? undefined : (byokKey || null),
                          ai_provider: byokProvider,
                        });
                        const r = await userAPI.getAISettings();
                        setAiSettings(r.data);
                        if (r.data.has_api_key) setByokKey("••••••••");
                        toast.success("API Key 已保存");
                      } catch { toast.error("保存失败"); }
                      setSavingKey(false);
                    }}
                    disabled={savingKey}
                    className="px-4 py-2 bg-brand-gradient text-white rounded-[14px] text-sm font-medium
                      shadow-brand-glow-sm hover:shadow-brand-glow transition flex items-center gap-2"
                  >
                    {savingKey ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    {savingKey ? "保存中..." : "保存"}
                  </button>
                  <button
                    onClick={async () => {
                      await userAPI.updateAISettings({ ai_api_key: null, ai_provider: null });
                      setByokKey("");
                      const r = await userAPI.getAISettings();
                      setAiSettings(r.data);
                      toast.success("已清除 API Key");
                    }}
                    className="px-4 py-2 text-gray-500 hover:text-red-600 rounded-[14px] text-sm transition"
                  >
                    清除
                  </button>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div className="animate-fade-in">
            <div className="flex items-center justify-between mb-5">
              <h2 className="section-title">我的策略</h2>
              <Link
                href="/strategy/new/edit"
                className="flex items-center gap-2 px-4 py-2 bg-brand-gradient text-white
                  rounded-[14px] text-sm font-medium
                  shadow-brand-glow-sm hover:shadow-brand-glow
                  hover:-translate-y-px active:translate-y-0 transition"
              >
                <PlusCircle size={16} />
                新建策略
              </Link>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 size={32} className="animate-spin text-gray-300 dark:text-gray-600" />
              </div>
            ) : strategies.length === 0 ? (
              <div className="text-center py-20 card-glass">
                <div className="w-16 h-16 rounded-[14px] bg-brand-50 dark:bg-brand-900/20
                  flex items-center justify-center mx-auto mb-4"
                >
                  <Sparkles size={28} className="text-brand-500" />
                </div>
                <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">还没有策略</h3>
                <p className="text-sm text-gray-500 mb-5">创建你的第一个量化策略，或让 AI 帮你生成</p>
                <Link
                  href="/strategy/new/edit"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-brand-gradient text-white
                    rounded-[14px] text-sm font-medium shadow-brand-glow-sm hover:shadow-brand-glow transition"
                >
                  <PlusCircle size={16} />
                  新建策略
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {strategies.map((s) => (
                  <div
                    key={s.id}
                    className="card-horizon p-5 flex items-center justify-between hover:-translate-y-0.5 transition-all duration-300"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-semibold text-gray-900 dark:text-white truncate">{s.name}</h3>
                        <span className={clsx(
                          "text-xs px-2 py-0.5 rounded-full font-medium",
                          s.status === "draft"
                            ? "bg-amber-50 dark:bg-amber-900/20 text-amber-600"
                            : "bg-green-50 dark:bg-green-900/20 text-profit"
                        )}>
                          {s.status === "draft" ? "草稿" : "已保存"}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-gray-400">
                        <Clock size={11} />
                        {new Date(s.updated_at).toLocaleString("zh-CN")}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 ml-4">
                      <button
                        onClick={() => router.push(`/strategy/${s.id}/edit`)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300
                          hover:bg-gray-100 dark:hover:bg-navy-700/50 rounded-[12px] transition"
                      >
                        <Edit3 size={14} />
                        <span className="hidden sm:inline">编辑</span>
                      </button>
                      <button
                        onClick={() => handleBacktest(s.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-white
                          bg-brand-gradient hover:shadow-brand-glow-sm rounded-[12px] transition"
                      >
                        <Play size={14} />
                        <span className="hidden sm:inline">回测</span>
                      </button>
                      <button
                        onClick={() => handleDelete(s.id, s.name)}
                        className="p-1.5 text-gray-400 hover:text-loss hover:bg-red-50 dark:hover:bg-red-900/20 rounded-[10px] transition"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div>
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6 bg-lightPrimary dark:bg-navy-900 min-h-[calc(100vh-57px)]">
          {renderTab()}
        </main>
      </div>

      {showTour && (
        <GuidedTour
          storageKey="qd_tour_dashboard"
          steps={[
            {
              selector: "a[href='/strategy/new/edit']",
              title: "创建你的第一个策略",
              content: "从这里开始。你可以选模板快速上手，也可以从空白画布自由搭建。",
              action: "点击「新建策略」按钮",
            },
            {
              selector: "nav a[href='/dashboard?tab=ai']",
              title: "AI 策略助手",
              content: "不会写策略？告诉 AI 你的想法，让它帮你生成。只需用大白话描述即可。",
              action: "点击侧边栏「AI 助手」试试",
            },
            {
              selector: "nav a[href='/dashboard?tab=backtests']",
              title: "回测记录",
              content: "所有回测结果都保存在这里，你可以随时回看净值曲线和交易明细。",
              action: "回测完成后来这里查看",
            },
            {
              selector: "nav a[href='/dashboard?tab=settings']",
              title: "设置与 Agent Token",
              content: "在这里管理账户设置，以及创建 Agent Token 让 AI 编辑器直接操控 QuantDesk。",
              action: "需要时进入设置创建 Token",
            },
          ]}
          onComplete={() => setShowTour(false)}
        />
      )}
    </div>
  );
}
