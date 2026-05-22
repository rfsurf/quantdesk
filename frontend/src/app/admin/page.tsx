"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { adminAPI } from "@/lib/api";
import {
  LayoutDashboard, Users, Code2, BarChart3, Key,
  Trash2, RefreshCw, Loader2, Shield, ArrowLeft,
  Activity, Globe, Database, Layers,
  CheckCircle, XCircle,
} from "lucide-react";
import clsx from "clsx";
import toast from "react-hot-toast";

type Tab = "overview" | "users" | "strategies" | "backtests" | "tokens";

export default function AdminPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("overview");
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<any[]>([]);
  const [backtests, setBacktests] = useState<any[]>([]);
  const [tokens, setTokens] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    setError("");
    try {
      const [s, u, str, bt, tok] = await Promise.all([
        adminAPI.stats(),
        adminAPI.users(),
        adminAPI.strategies(),
        adminAPI.backtests(),
        adminAPI.agentTokens(),
      ]);
      setStats(s.data);
      setUsers(u.data.items || []);
      setStrategies(str.data.items || []);
      setBacktests(bt.data.items || []);
      setTokens(tok.data.items || []);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "无权限访问管理后台";
      if (err.response?.status === 403) {
        setError("需要管理员权限。请使用管理员账号 admin@quantdesk.dev 登录。");
      } else {
        setError(msg);
      }
    }
    setLoading(false);
  };

  const handleDeleteUser = async (uid: string, email: string) => {
    if (!confirm(`确定删除用户"${email}"及其所有策略和回测数据？此操作不可撤销。`)) return;
    try { await adminAPI.deleteUser(uid); toast.success("用户已删除"); loadAll(); }
    catch { toast.error("删除失败"); }
  };

  const handleDeleteStrategy = async (sid: string, name: string) => {
    if (!confirm(`确定删除策略"${name}"？`)) return;
    try { await adminAPI.deleteStrategy(sid); toast.success("策略已删除"); loadAll(); }
    catch { toast.error("删除失败"); }
  };

  const handleDeleteBacktest = async (bid: string) => {
    if (!confirm("确定删除此回测记录？")) return;
    try { await adminAPI.deleteBacktest(bid); toast.success("回测已删除"); loadAll(); }
    catch { toast.error("删除失败"); }
  };

  const handleRevokeToken = async (tid: string, name: string) => {
    if (!confirm(`确定吊销 Agent Token "${name}"？`)) return;
    try { await adminAPI.revokeAgentToken(tid); toast.success("Token 已吊销"); loadAll(); }
    catch { toast.error("吊销失败"); }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-lightPrimary dark:bg-navy-900 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-brand-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-lightPrimary dark:bg-navy-900 flex items-center justify-center">
        <div className="text-center max-w-md animate-fade-in-up">
          <div className="w-16 h-16 bg-loss/10 rounded-[16px] flex items-center justify-center mx-auto mb-4">
            <Shield size={28} className="text-loss" />
          </div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white mb-2">访问受限</h1>
          <p className="text-gray-500 text-sm mb-6">{error}</p>
          <Link href="/dashboard"
            className="inline-flex items-center gap-2 px-4 py-2 bg-brand-gradient text-white rounded-[14px] text-sm font-medium shadow-brand-glow-sm transition"
          >
            <ArrowLeft size={14} />
            返回仪表盘
          </Link>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; icon: any; count?: number }[] = [
    { key: "overview", label: "概览", icon: LayoutDashboard },
    { key: "users", label: "用户", icon: Users, count: users.length },
    { key: "strategies", label: "策略", icon: Code2, count: strategies.length },
    { key: "backtests", label: "回测", icon: BarChart3, count: backtests.length },
    { key: "tokens", label: "Token", icon: Key, count: tokens.length },
  ];

  return (
    <div className="min-h-screen bg-lightPrimary dark:bg-navy-900">
      {/* Admin header */}
      <div className="bg-navy-800 text-white sticky top-0 z-50 shadow-soft">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-gray-400 hover:text-white transition p-1.5 rounded-[10px] hover:bg-navy-700">
              <ArrowLeft size={18} />
            </Link>
            <div className="w-8 h-8 rounded-[10px] bg-brand-gradient flex items-center justify-center">
              <Shield size={16} className="text-white" />
            </div>
            <span className="font-bold">QuantDesk 管理后台</span>
          </div>
          <button
            onClick={loadAll}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition px-2.5 py-1.5 rounded-[10px] hover:bg-navy-700"
          >
            <RefreshCw size={14} />
            刷新
          </button>
        </div>
        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-6 flex gap-0">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={clsx(
                "flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition",
                tab === t.key
                  ? "border-brand-400 text-white font-medium"
                  : "border-transparent text-gray-400 hover:text-gray-200"
              )}
            >
              <t.icon size={15} />
              {t.label}
              {t.count !== undefined && (
                <span className="bg-navy-700 text-gray-300 text-xs px-1.5 py-0.5 rounded-[6px]">{t.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {tab === "overview" && stats && (
          <div className="space-y-6 animate-fade-in">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="用户" value={stats.users} icon={Users} color="brand" />
              <StatCard label="策略" value={stats.strategies} icon={Code2} color="purple" />
              <StatCard label="回测" value={stats.backtests} icon={BarChart3} color="profit" />
              <StatCard label="活跃 Token" value={stats.agent_tokens} icon={Key} color="amber" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="回测完成" value={stats.backtests_done} icon={CheckCircle} color="profit" />
              <StatCard label="回测失败" value={stats.backtests_failed} icon={XCircle} color="loss" />
              <StatCard label="已吊销Token" value={stats.agent_tokens_revoked} icon={Activity} color="gray" />
              <StatCard label="运行时间(h)" value={stats.uptime_hours?.toFixed(1) || "-"} icon={Globe} color="blue" />
            </div>

            {/* System Status */}
            <div className="card-glass p-6">
              <h3 className="font-bold text-gray-900 dark:text-white mb-4">系统状态</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <StatusItem label="API 健康" status={stats.api_health} />
                <StatusItem label="数据库" status="connected" />
                <StatusItem label="Redis" status="connected" />
                <StatusItem label="后端版本" status="v2.0" />
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Backtest Success Rate */}
              <div className="card-glass p-6">
                <h3 className="font-bold text-gray-900 dark:text-white mb-4">回测成功率</h3>
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <div className="h-8 bg-gray-100 dark:bg-navy-700 rounded-[10px] overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-[10px] transition-all duration-500"
                        style={{ width: `${stats.backtests > 0 ? (stats.backtests_done / stats.backtests * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-bold text-green-500">
                      {stats.backtests > 0 ? Math.round(stats.backtests_done / stats.backtests * 100) : 0}%
                    </span>
                    <p className="text-xs text-gray-400">{stats.backtests_done}/{stats.backtests} 完成</p>
                  </div>
                </div>
                <div className="mt-3 flex gap-4 text-xs">
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-green-500" />完成 {stats.backtests_done}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-red-500" />失败 {stats.backtests_failed}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-gray-400" />待处理 {stats.backtests - stats.backtests_done - stats.backtests_failed}
                  </span>
                </div>
              </div>

              {/* Resource Usage */}
              <div className="card-glass p-6">
                <h3 className="font-bold text-gray-900 dark:text-white mb-4">资源分布</h3>
                <div className="space-y-3">
                  <ProgressBar label="用户" value={stats.users} max={100} color="blue" />
                  <ProgressBar label="策略" value={stats.strategies} max={100} color="purple" />
                  <ProgressBar label="回测任务" value={stats.backtests} max={100} color="green" />
                  <ProgressBar label="Agent Token" value={stats.agent_tokens} max={50} color="amber" />
                </div>
              </div>
            </div>

            {/* Recent */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card-glass p-6">
                <h3 className="font-bold text-gray-900 dark:text-white mb-4 text-sm">最近注册用户</h3>
                <div className="space-y-2">
                  {users.slice(0, 5).map((u) => (
                    <div key={u.id} className="flex items-center justify-between py-2 text-sm">
                      <span className="text-gray-700 dark:text-gray-300">{u.email}</span>
                      <span className="text-xs text-gray-400">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString("zh-CN") : "-"}
                      </span>
                    </div>
                  ))}
                  {users.length === 0 && <p className="text-gray-400 text-sm py-4 text-center">暂无用户</p>}
                </div>
              </div>
              <div className="card-glass p-6">
                <h3 className="font-bold text-gray-900 dark:text-white mb-4 text-sm">最新策略</h3>
                <div className="space-y-2">
                  {strategies.slice(0, 5).map((s) => (
                    <div key={s.id} className="flex items-center justify-between py-2 text-sm">
                      <span className="text-gray-700 dark:text-gray-300 truncate max-w-[60%]">{s.name}</span>
                      <span className="text-xs text-gray-400">{s.user_email}</span>
                    </div>
                  ))}
                  {strategies.length === 0 && <p className="text-gray-400 text-sm py-4 text-center">暂无策略</p>}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Table */}
        {tab === "users" && (
          <DataTable
            title="用户列表"
            count={users.length}
            headers={["邮箱", "套餐", "策略数", "回测数", "注册时间", "操作"]}
            data={users}
            renderRow={(u) => (
              <>
                <td className="px-4 py-2.5 text-gray-800 dark:text-gray-200">{u.email}</td>
                <td className="px-4 py-2.5">
                  <span className={clsx(
                    "text-xs px-2 py-0.5 rounded-[8px] font-medium",
                    u.plan === "pro" ? "bg-brand-100 dark:bg-brand-900/30 text-brand-600" : "bg-gray-100 dark:bg-navy-700 text-gray-500"
                  )}>
                    {u.plan}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-800 dark:text-gray-200">{u.strategy_count}</td>
                <td className="px-4 py-2.5 text-gray-800 dark:text-gray-200">{u.backtest_count}</td>
                <td className="px-4 py-2.5 text-xs text-gray-400">
                  {u.created_at ? new Date(u.created_at).toLocaleString("zh-CN") : "-"}
                </td>
                <td className="px-4 py-2.5">
                  <button onClick={() => handleDeleteUser(u.id, u.email)}
                    className="text-xs text-loss/70 hover:text-loss transition p-1 rounded-[8px] hover:bg-red-50"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </>
            )}
            emptyText="暂无用户"
          />
        )}

        {/* Strategies Table */}
        {tab === "strategies" && (
          <DataTable
            title="策略列表"
            count={strategies.length}
            headers={["名称", "用户", "状态", "更新日期", "操作"]}
            data={strategies}
            renderRow={(s) => (
              <>
                <td className="px-4 py-2.5 font-medium text-gray-800 dark:text-gray-200">{s.name}</td>
                <td className="px-4 py-2.5 text-xs text-gray-500">{s.user_email}</td>
                <td className="px-4 py-2.5">
                  <span className={clsx(
                    "text-xs px-2 py-0.5 rounded-[8px] font-medium",
                    s.status === "draft" ? "bg-amber-50 dark:bg-amber-900/20 text-amber-600" : "bg-green-50 dark:bg-green-900/20 text-profit"
                  )}>
                    {s.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-400">
                  {s.updated_at ? new Date(s.updated_at).toLocaleString("zh-CN") : "-"}
                </td>
                <td className="px-4 py-2.5">
                  <button onClick={() => handleDeleteStrategy(s.id, s.name)}
                    className="text-xs text-loss/70 hover:text-loss transition p-1 rounded-[8px] hover:bg-red-50"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </>
            )}
            emptyText="暂无策略"
          />
        )}

        {/* Backtests Table */}
        {tab === "backtests" && (
          <DataTable
            title="回测记录"
            count={backtests.length}
            headers={["策略", "用户", "状态", "时间", "操作"]}
            data={backtests}
            renderRow={(b) => (
              <>
                <td className="px-4 py-2.5 text-gray-800 dark:text-gray-200">{b.strategy_name}</td>
                <td className="px-4 py-2.5 text-xs text-gray-500">{b.user_email}</td>
                <td className="px-4 py-2.5">
                  <span className={clsx(
                    "text-xs px-2 py-0.5 rounded-[8px] font-medium",
                    b.status === "done" ? "bg-green-50 dark:bg-green-900/20 text-profit" :
                    b.status === "failed" ? "bg-red-50 dark:bg-red-900/20 text-loss" :
                    "bg-gray-100 dark:bg-navy-700 text-gray-500"
                  )}>
                    {b.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-400">
                  {b.created_at ? new Date(b.created_at).toLocaleString("zh-CN") : "-"}
                </td>
                <td className="px-4 py-2.5">
                  <button onClick={() => handleDeleteBacktest(b.id)}
                    className="text-xs text-loss/70 hover:text-loss transition p-1 rounded-[8px] hover:bg-red-50"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </>
            )}
            emptyText="暂无回测记录"
          />
        )}

        {/* Tokens Table */}
        {tab === "tokens" && (
          <DataTable
            title="Agent Token 列表"
            count={tokens.length}
            headers={["名称", "权限", "用户", "状态", "最近使用", "操作"]}
            data={tokens}
            renderRow={(t) => (
              <>
                <td className="px-4 py-2.5 font-mono text-xs text-gray-800 dark:text-gray-200">{t.name}</td>
                <td className="px-4 py-2.5">
                  <div className="flex gap-1">
                    {t.scopes?.map((s: string) => (
                      <span key={s} className="text-xs bg-gray-100 dark:bg-navy-700 px-1.5 py-0.5 rounded-[6px] text-gray-600 dark:text-gray-400">
                        {s}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-500">{t.user_email}</td>
                <td className="px-4 py-2.5">
                  <span className={clsx(
                    "text-xs px-2 py-0.5 rounded-[8px] font-medium",
                    t.is_revoked ? "bg-red-50 dark:bg-red-900/20 text-loss" : "bg-green-50 dark:bg-green-900/20 text-profit"
                  )}>
                    {t.is_revoked ? "已吊销" : "活跃"}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-xs text-gray-400">
                  {t.last_used_at ? new Date(t.last_used_at).toLocaleString("zh-CN") : "从未使用"}
                </td>
                <td className="px-4 py-2.5">
                  {!t.is_revoked && (
                    <button onClick={() => handleRevokeToken(t.id, t.name)}
                      className="text-xs text-loss/70 hover:text-loss transition"
                    >
                      吊销
                    </button>
                  )}
                </td>
              </>
            )}
            emptyText="暂无 Token"
          />
        )}
      </div>
    </div>
  );
}

/* ---------- Reusable Components ---------- */

function StatCard({ label, value, icon: Icon, color = "brand" }: { label: string; value: number | string; icon: any; color?: string }) {
  const colorStyles: Record<string, string> = {
    brand: "bg-brand-50 dark:bg-brand-900/15 text-brand-600",
    purple: "bg-purple-50 dark:bg-purple-900/15 text-purple-600",
    profit: "bg-green-50 dark:bg-green-900/15 text-profit",
    loss: "bg-red-50 dark:bg-red-900/15 text-loss",
    amber: "bg-amber-50 dark:bg-amber-900/15 text-amber-600",
    gray: "bg-gray-50 dark:bg-navy-700/60 text-gray-600",
    blue: "bg-blue-50 dark:bg-blue-900/15 text-blue-600",
  };
  return (
    <div className={`rounded-[18px] p-4 ${colorStyles[color] || colorStyles.brand}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium opacity-70">{label}</span>
        <Icon size={14} className="opacity-50" />
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}

function StatusItem({ label, status }: { label: string; status: string }) {
  const isOk = status === "ok" || status === "connected" || status === "v2.0";
  return (
    <div className="flex items-center gap-2 p-3 rounded-[12px] bg-white/50 dark:bg-navy-700/50">
      <div className={`w-2.5 h-2.5 rounded-full ${isOk ? "bg-profit" : "bg-loss"}`} />
      <span className="text-gray-600 dark:text-gray-300 text-sm">{label}</span>
      <span className="font-medium text-gray-800 dark:text-white ml-auto text-sm">{status}</span>
    </div>
  );
}

function ProgressBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const percentage = Math.min((value / max) * 100, 100);
  const colorStyles: Record<string, string> = {
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    green: "bg-green-500",
    amber: "bg-amber-500",
  };
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-gray-500 w-24">{label}</span>
      <div className="flex-1 h-3 bg-gray-100 dark:bg-navy-700 rounded-[6px] overflow-hidden">
        <div
          className={`h-full ${colorStyles[color] || "bg-gray-500"} rounded-[6px] transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-12 text-right">{value}</span>
    </div>
  );
}

function DataTable({
  title, count, headers, data, renderRow, emptyText
}: {
  title: string;
  count: number;
  headers: string[];
  data: any[];
  renderRow: (item: any) => React.ReactNode;
  emptyText: string;
}) {
  return (
    <div className="card-glass overflow-hidden animate-fade-in">
      <div className="px-5 py-4 border-b border-gray-100 dark:border-navy-600/50 flex items-center justify-between">
        <h3 className="font-bold text-gray-900 dark:text-white">{title}</h3>
        <span className="text-xs text-gray-400">{count} 条记录</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 text-xs border-b border-gray-100 dark:border-navy-600/50">
              {headers.map((h) => (
                <th key={h} className="px-4 py-2 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, idx) => (
              <tr key={item.id || idx}
                className="border-b border-gray-50 dark:border-navy-600/30 hover:bg-gray-50/50 dark:hover:bg-navy-700/30 transition"
              >
                {renderRow(item)}
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={headers.length} className="text-center py-8 text-gray-400">{emptyText}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
