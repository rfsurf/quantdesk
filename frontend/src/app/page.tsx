"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Zap, BarChart3, Rocket, ArrowRight, Check } from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (localStorage.getItem("token")) router.push("/dashboard");
  }, [router]);

  const handleQuickStart = async () => {
    if (!email || !password) return;
    setLoading(true);
    try {
      const { authAPI } = await import("@/lib/api");
      await authAPI.sendCode(email);
      await authAPI.register(email, password, "000000");
      const r = await authAPI.login(email, password);
      localStorage.setItem("token", r.data.access_token);
      router.push("/onboarding");
    } catch {
      try {
        const { authAPI } = await import("@/lib/api");
        const r = await authAPI.login(email, password);
        localStorage.setItem("token", r.data.access_token);
        router.push("/dashboard");
      } catch {
        alert("登录失败，请检查密码");
      }
    }
    setLoading(false);
  };

  const features = [
    {
      icon: <Sparkles size={28} className="text-brand-500" />,
      title: "拖拽搭建",
      desc: "左侧因子列表直接拖到画布，像搭积木一样连线组合。20+ 技术指标 + 基本面因子，不需要写一行代码。",
    },
    {
      icon: <Zap size={28} className="text-amber-500" />,
      title: "秒级回测",
      desc: "点一下按钮，3 秒出结果。净值曲线、最大回撤、夏普比率、月度热力图，全部可视化展示。",
    },
    {
      icon: <Rocket size={28} className="text-blue-500" />,
      title: "一键QMT",
      desc: "回测通过后，一键下载 Python 脚本，放到本地 QMT 就能跑实盘。Pro 版支持实时信号推送。",
    },
  ];

  return (
    <div className="min-h-screen bg-hero-gradient dark:bg-hero-gradient-dark transition-colors duration-300">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4
        bg-white/60 dark:bg-navy-800/60 backdrop-blur-nav
        border-b border-gray-100/50 dark:border-navy-700/50"
      >
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 bg-brand-gradient rounded-[12px]
            flex items-center justify-center text-white font-bold text-sm
            shadow-brand-glow-sm group-hover:shadow-brand-glow transition"
          >
            <Sparkles size={16} />
          </div>
          <span className="text-lg font-bold text-gray-800 dark:text-white">QuantDesk</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link
            href="/admin"
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-brand-500 transition"
          >
            管理后台
          </Link>
          <Link
            href="/login"
            className="px-4 py-2 bg-brand-gradient text-white rounded-[16px] text-sm font-semibold
              shadow-brand-glow-sm hover:shadow-brand-glow
              hover:-translate-y-px active:translate-y-0 transition"
          >
            登录
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-16 pb-12 text-center animate-fade-in-up">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full
          bg-brand-100/80 dark:bg-brand-900/30
          text-brand-600 dark:text-brand-300
          text-xs font-semibold mb-8 border border-brand-200/50 dark:border-brand-800/50"
        >
          <BarChart3 size={13} />
          零代码 · 可视化 · 一键回测
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 dark:text-white leading-tight mb-5 tracking-tight">
          不用写一行代码
          <br />
          <span className="text-gradient">搭建你的量化策略</span>
        </h1>
        <p className="text-lg text-gray-500 dark:text-gray-400 max-w-xl mx-auto mb-10 leading-relaxed">
          像搭积木一样拖拽因子、连线组合条件，3 分钟完成策略回测，一键导出到 QMT 实盘。
        </p>

        {/* Quick register card */}
        <div className="max-w-md mx-auto card-glass p-8">
          <div className="text-left mb-5">
            <h3 className="font-bold text-gray-900 dark:text-white text-lg">免费开始</h3>
            <p className="text-sm text-gray-400 mt-1">输入邮箱，立刻体验</p>
          </div>
          <input
            type="email" placeholder="输入邮箱" value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input-horizon w-full px-4 py-3 mb-3 text-sm"
          />
          <input
            type="password" placeholder="设置密码（至少8位）" value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-horizon w-full px-4 py-3 mb-4 text-sm"
          />
          <button
            onClick={handleQuickStart}
            disabled={loading || !email || password.length < 8}
            className="w-full py-3 bg-brand-gradient text-white rounded-[16px] font-semibold
              shadow-brand-glow-sm hover:shadow-brand-glow
              hover:-translate-y-px active:translate-y-0
              disabled:opacity-40 transition-all duration-300
              flex items-center justify-center gap-2"
          >
            {loading ? "处理中..." : (
              <>
                免费注册，立即体验
                <ArrowRight size={16} />
              </>
            )}
          </button>
          <p className="text-xs text-gray-400 mt-3">验证码自动填充，无需邮箱验证</p>
        </div>
      </section>

      {/* Features */}
      <section className="border-y border-gray-100/80 dark:border-navy-700/50 py-20 bg-white/40 dark:bg-navy-800/30">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">核心功能</h2>
            <p className="text-gray-500 dark:text-gray-400">为量化交易者打造的一站式工作台</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div
                key={i}
                className="card-horizon p-7 text-center hover:-translate-y-1 transition-all duration-400"
              >
                <div className="w-14 h-14 rounded-[14px] bg-gray-50 dark:bg-navy-700/50
                  flex items-center justify-center mx-auto mb-4"
                >
                  {f.icon}
                </div>
                <h3 className="font-bold text-gray-900 dark:text-white mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Plans */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">选择你的计划</h2>
            <p className="text-gray-500 dark:text-gray-400">从免费开始，随时升级</p>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {/* Free */}
            <div className="card-horizon p-7">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-semibold text-gray-500 dark:text-gray-400">Free</span>
                <span className="text-2xl font-bold text-gray-900 dark:text-white">免费</span>
              </div>
              <div className="space-y-3 mb-6">
                {[
                  "策略创建与编辑",
                  "基础回测（月度数据）",
                  "AI 策略生成（3次/月）",
                  "QMT 脚本导出",
                ].map((item) => (
                  <div key={item} className="flex items-center gap-2.5 text-sm text-gray-600 dark:text-gray-300">
                    <Check size={14} className="text-brand-500" />
                    {item}
                  </div>
                ))}
              </div>
            </div>

            {/* Pro */}
            <div className="card-horizon p-7 border-brand-200/60 dark:border-brand-800/40 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-brand-gradient text-white text-xs font-semibold px-3 py-1 rounded-bl-[14px]">
                推荐
              </div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-semibold text-brand-600 dark:text-brand-400">Pro</span>
                <span className="text-2xl font-bold text-gray-900 dark:text-white">¥99<span className="text-sm font-normal text-gray-400">/月</span></span>
              </div>
              <div className="space-y-3 mb-6">
                {[
                  "所有 Free 功能",
                  "高频回测（日线数据）",
                  "AI 策略生成（500次/月）",
                  "参数优化 + WFA",
                  "自带 API Key（BYOK）",
                  "Agent Token（MCP 集成）",
                ].map((item) => (
                  <div key={item} className="flex items-center gap-2.5 text-sm text-gray-600 dark:text-gray-300">
                    <Check size={14} className="text-brand-500" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100/80 dark:border-navy-700/50 py-8 bg-white/40 dark:bg-navy-800/30">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-brand-gradient rounded-[8px] flex items-center justify-center">
              <Sparkles size={14} className="text-white" />
            </div>
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">QuantDesk</span>
          </div>
          <span className="text-sm text-gray-400 dark:text-gray-500">面向中国散户的个人量化工作台</span>
        </div>
      </footer>
    </div>
  );
}
