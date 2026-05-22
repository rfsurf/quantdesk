"use client";
import { useState, useEffect, Suspense } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/Sidebar";
import { agentAPI } from "@/lib/api";
import {
  Plus, Trash2, Copy, Check, Key, Shield, Clock, Eye, EyeOff, ArrowLeft,
  Loader2, Sparkles, Lock,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";

export default function AgentTokensPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">
      <Loader2 size={32} className="animate-spin text-gray-300 dark:text-gray-600" />
    </div>}>
      <AgentTokensContent />
    </Suspense>
  );
}

function AgentTokensContent() {
  const router = useRouter();
  const [tokens, setTokens] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newToken, setNewToken] = useState({ name: "", scopes: ["R", "B", "W"], expires_in_days: 90 });
  const [revealedToken, setRevealedToken] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    fetchTokens();
  }, []);

  const fetchTokens = async () => {
    try {
      const r = await agentAPI.list();
      setTokens(r.data || []);
    } catch { toast.error("加载 Token 列表失败"); }
    setLoading(false);
  };

  const handleCreate = async () => {
    if (!newToken.name.trim()) return toast.error("请输入 Token 名称");
    try {
      const r = await agentAPI.create(newToken);
      setRevealedToken(r.data.token);
      setShowCreate(false);
      setNewToken({ name: "", scopes: ["R", "B", "W"], expires_in_days: 90 });
      fetchTokens();
      toast.success("Token 已创建");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "创建失败");
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm("确定吊销此 Token？吊销后无法恢复。")) return;
    try {
      await agentAPI.revoke(id);
      fetchTokens();
      toast.success("Token 已吊销");
    } catch { toast.error("吊销失败"); }
  };

  const copyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    setCopiedId(token);
    setTimeout(() => setCopiedId(null), 2000);
    toast.success("已复制到剪贴板");
  };

  const toggleScope = (scope: string) => {
    setNewToken(prev => ({
      ...prev,
      scopes: prev.scopes.includes(scope)
        ? prev.scopes.filter(s => s !== scope)
        : [...prev.scopes, scope],
    }));
  };

  const SCOPE_LABELS: Record<string, string> = {
    R: "读取数据", B: "运行回测", W: "创建策略",
    N: "通知", C: "配置", T: "实盘交易",
  };

  const SCOPE_COLORS: Record<string, string> = {
    R: "bg-blue-50 dark:bg-blue-900/20 text-blue-600",
    B: "bg-purple-50 dark:bg-purple-900/20 text-purple-600",
    W: "bg-green-50 dark:bg-green-900/20 text-profit",
    N: "bg-amber-50 dark:bg-amber-900/20 text-amber-600",
    C: "bg-gray-50 dark:bg-navy-700 text-gray-600",
    T: "bg-red-50 dark:bg-red-900/20 text-loss",
  };

  return (
    <div>
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6 bg-lightPrimary dark:bg-navy-900 min-h-[calc(100vh-57px)]">
          <div className="max-w-3xl mx-auto animate-fade-in">
            {/* Header */}
            <div className="flex items-center gap-3 mb-5">
              <Link href="/dashboard?tab=settings"
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-navy-700 rounded-[10px] transition"
              >
                <ArrowLeft size={18} />
              </Link>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">Agent Tokens</h1>
              <span className="text-xs bg-gray-100 dark:bg-navy-700 text-gray-500 px-2 py-1 rounded-[10px]">
                MCP Gateway
              </span>
            </div>

            <p className="text-sm text-gray-500 mb-6">
              创建 Agent Token 后，可在 Claude Code / Cursor / Codex 等 AI 编辑器中操控 QuantDesk。
            </p>

            {/* Revealed Token */}
            {revealedToken && (
              <div className="mb-5 p-5 bg-amber-50/80 dark:bg-amber-900/15 border border-amber-200/50 rounded-[18px]">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 rounded-[10px] bg-amber-100 flex items-center justify-center">
                    <Key size={16} className="text-amber-600" />
                  </div>
                  <span className="text-sm font-semibold text-amber-800">Token 已创建（仅显示一次）</span>
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2.5 bg-white border border-amber-200 rounded-[12px] text-xs break-all select-all">
                    {revealedToken}
                  </code>
                  <button
                    onClick={() => copyToken(revealedToken)}
                    className="p-2.5 text-amber-600 hover:bg-amber-100 rounded-[12px] transition"
                  >
                    {copiedId === revealedToken ? <Check size={16} /> : <Copy size={16} />}
                  </button>
                </div>
                <button
                  onClick={() => setRevealedToken(null)}
                  className="text-xs text-amber-600 mt-3 hover:underline"
                >
                  我已保存，关闭
                </button>
              </div>
            )}

            {/* Token List */}
            <div className="card-glass overflow-hidden mb-5">
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-navy-600/50">
                <h2 className="font-bold text-gray-800 dark:text-white">我的 Tokens</h2>
                <button
                  onClick={() => setShowCreate(!showCreate)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-brand-600
                    hover:bg-brand-50 dark:hover:bg-brand-900/20 rounded-[12px] transition"
                >
                  <Plus size={16} />
                  创建
                </button>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 size={24} className="animate-spin text-gray-300 dark:text-gray-600" />
                </div>
              ) : tokens.length === 0 ? (
                <div className="text-center py-16 text-gray-400">
                  <div className="w-14 h-14 rounded-[14px] bg-gray-50 dark:bg-navy-700/50 flex items-center justify-center mx-auto mb-3">
                    <Key size={24} className="text-gray-300 dark:text-gray-600" />
                  </div>
                  <p className="text-sm font-medium">还没有 Agent Token</p>
                  <p className="text-xs mt-1">创建一个来让 AI 编辑器操控你的量化策略</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50 dark:divide-navy-700/40">
                  {tokens.map((t: any) => (
                    <div key={t.id}
                      className="px-5 py-4 flex items-center justify-between hover:bg-gray-50/50 dark:hover:bg-navy-700/30 transition"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-[12px] flex items-center justify-center ${
                          t.is_revoked ? "bg-gray-50 dark:bg-navy-700" : "bg-brand-50 dark:bg-brand-900/20"
                        }`}>
                          <Shield size={15} className={t.is_revoked ? "text-gray-400" : "text-brand-500"} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-800 dark:text-white">{t.name}</p>
                          <div className="flex items-center gap-1 mt-0.5">
                            {t.scopes.map((s: string) => (
                              <span key={s}
                                className={`text-[10px] px-1.5 py-0.5 rounded-[6px] font-medium ${
                                  SCOPE_COLORS[s] || "bg-gray-100 text-gray-500"
                                }`}
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                          t.is_revoked ? "bg-red-50 dark:bg-red-900/20 text-loss" : "bg-green-50 dark:bg-green-900/20 text-profit"
                        }`}>
                          {t.is_revoked ? "已吊销" : "活跃"}
                        </span>
                        {!t.is_revoked && (
                          <button
                            onClick={() => handleRevoke(t.id)}
                            className="p-2 text-gray-300 hover:text-loss hover:bg-red-50 dark:hover:bg-red-900/20 rounded-[10px] transition"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Create Panel */}
            {showCreate && (
              <div className="card-glass border-brand-200/50 dark:border-brand-800/40 p-6">
                <h3 className="font-bold text-gray-800 dark:text-white mb-4">创建新 Token</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1.5">名称</label>
                    <input
                      type="text"
                      value={newToken.name}
                      onChange={e => setNewToken(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="如: Cursor 工作区、Claude Code 策略"
                      className="input-horizon w-full px-3 py-2.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-2">权限范围 (Scopes)</label>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(SCOPE_LABELS).map(([scope, label]) => (
                        <button
                          key={scope}
                          onClick={() => toggleScope(scope)}
                          className={`px-3 py-1.5 rounded-[12px] text-xs font-medium transition ${
                            newToken.scopes.includes(scope)
                              ? "bg-brand-gradient text-white shadow-brand-glow-sm"
                              : "bg-gray-50 dark:bg-navy-700/60 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-navy-600"
                          }`}
                        >
                          {scope} — {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 dark:text-gray-300 mb-1.5">有效期 (天)</label>
                    <select
                      value={newToken.expires_in_days}
                      onChange={e => setNewToken(prev => ({ ...prev, expires_in_days: +e.target.value }))}
                      className="input-horizon px-3 py-2.5 text-sm cursor-pointer"
                    >
                      <option value={30}>30 天</option>
                      <option value={90}>90 天</option>
                      <option value={180}>180 天</option>
                      <option value={365}>365 天</option>
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={handleCreate}
                      className="px-5 py-2.5 bg-brand-gradient text-white rounded-[14px] text-sm font-medium
                        shadow-brand-glow-sm hover:shadow-brand-glow transition"
                    >
                      创建 Token
                    </button>
                    <button
                      onClick={() => setShowCreate(false)}
                      className="px-5 py-2.5 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-navy-700/50 rounded-[14px] text-sm transition"
                    >
                      取消
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
