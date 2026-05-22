"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authAPI } from "@/lib/api";
import { useAuthStore } from "@/store";
import { Sparkles, Mail, Lock, Loader2, ArrowRight } from "lucide-react";
import toast from "react-hot-toast";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);

  const handleSendCode = async () => {
    if (!email) return toast.error("请输入邮箱");
    try {
      await authAPI.sendCode(email);
      setCodeSent(true);
      toast.success("验证码已发送（开发模式自动填充 000000）");
    } catch {
      toast.error("发送失败");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return toast.error("请填写完整");
    setLoading(true);
    try {
      if (isRegister) {
        if (!code) return toast.error("请输入验证码");
        await authAPI.register(email, password, code);
      }
      const r = await authAPI.login(email, password);
      const token = r.data.access_token;
      setAuth(token, { id: r.data.user_id || "", email });
      toast.success(isRegister ? "注册成功" : "登录成功");
      router.push("/dashboard");
    } catch (err: any) {
      const msg = err.response?.data?.detail || "操作失败";
      toast.error(msg);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center
      bg-lightPrimary dark:bg-navy-900 px-4"
    >
      <div className="w-full max-w-md animate-fade-in-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2.5">
            <div className="w-12 h-12 bg-brand-gradient rounded-[14px]
              flex items-center justify-center text-white font-bold text-lg
              shadow-brand-glow-sm"
            >
              <Sparkles size={20} />
            </div>
            <span className="text-2xl font-bold text-gray-900 dark:text-white">QuantDesk</span>
          </Link>
          <p className="text-gray-500 dark:text-gray-400 mt-3 text-sm">
            {isRegister ? "创建账号，开始你的量化之旅" : "欢迎回来"}
          </p>
        </div>

        {/* Card */}
        <form
          onSubmit={handleSubmit}
          className="card-glass p-7 sm:p-8"
        >
          {/* Email */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">邮箱</label>
            <div className="relative">
              <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-horizon w-full pl-10 pr-4 py-2.5 text-sm"
                placeholder="your@email.com"
              />
            </div>
          </div>

          {/* Code for register */}
          {isRegister && (
            <div className="mb-4 flex gap-2 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">验证码</label>
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="input-horizon w-full px-4 py-2.5 text-sm"
                  placeholder="输入验证码"
                  maxLength={6}
                />
              </div>
              <button
                type="button"
                onClick={handleSendCode}
                className="px-4 py-2.5 bg-gray-100 dark:bg-navy-600/60
                  text-gray-700 dark:text-gray-300
                  rounded-[14px] text-sm font-medium
                  hover:bg-gray-200 dark:hover:bg-navy-500/60 transition"
              >
                {codeSent ? "已发送" : "获取验证码"}
              </button>
            </div>
          )}

          {/* Password */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">密码</label>
            <div className="relative">
              <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-horizon w-full pl-10 pr-4 py-2.5 text-sm"
                placeholder="至少8位"
              />
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-brand-gradient text-white rounded-[16px] font-semibold
              shadow-brand-glow-sm hover:shadow-brand-glow
              hover:-translate-y-px active:translate-y-0
              disabled:opacity-40 transition-all duration-300
              flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : null}
            {loading ? "处理中..." : isRegister ? "注册" : "登录"}
            {!loading && <ArrowRight size={16} />}
          </button>

          {/* Toggle */}
          <div className="mt-5 text-center">
            <button
              type="button"
              onClick={() => setIsRegister(!isRegister)}
              className="text-sm text-brand-600 dark:text-brand-400 font-medium
                hover:underline transition"
            >
              {isRegister ? "已有账号？去登录" : "没有账号？免费注册"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
