import clsx from "clsx";
import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "outline" | "glass";
  size?: "sm" | "md" | "lg";
  glow?: boolean;
  fullWidth?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  glow = false,
  fullWidth = false,
  children,
  className,
  ...props
}: ButtonProps) {
  const variants = {
    primary: clsx(
      "bg-brand-gradient text-white",
      "shadow-soft hover:shadow-card-hover",
      "hover:-translate-y-px active:translate-y-0",
      glow && "shadow-brand-glow hover:shadow-brand-glow-sm"
    ),
    secondary: clsx(
      "bg-white dark:bg-navy-700",
      "border border-gray-200/80 dark:border-navy-600/80",
      "text-gray-700 dark:text-gray-300",
      "hover:bg-gray-50 dark:hover:bg-navy-600/60",
      "hover:border-gray-300 dark:hover:border-navy-500"
    ),
    ghost: clsx(
      "text-gray-600 dark:text-gray-400",
      "hover:bg-gray-100/80 dark:hover:bg-navy-700/60",
      "hover:text-gray-800 dark:hover:text-white"
    ),
    danger: clsx(
      "bg-loss/10 dark:bg-loss/10",
      "text-loss",
      "hover:bg-loss/20 dark:hover:bg-loss/20",
      "border border-loss/20"
    ),
    outline: clsx(
      "bg-transparent",
      "border border-brand-200 dark:border-brand-800",
      "text-brand-600 dark:text-brand-400",
      "hover:bg-brand-50 dark:hover:bg-brand-900/20",
      "hover:border-brand-300 dark:hover:border-brand-700"
    ),
    glass: clsx(
      "bg-white/60 dark:bg-navy-700/40",
      "backdrop-blur-sm",
      "border border-white/30 dark:border-white/10",
      "text-gray-700 dark:text-gray-300",
      "hover:bg-white/80 dark:hover:bg-navy-700/60"
    ),
  };

  const sizes = {
    sm: "px-3 py-1.5 text-xs rounded-[14px]",
    md: "px-4 py-2 text-sm rounded-[16px]",
    lg: "px-6 py-3 text-sm font-semibold rounded-[16px]",
  };

  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 font-medium",
        "transition-all duration-300",
        "disabled:opacity-40 disabled:pointer-events-none disabled:transform-none",
        variants[variant],
        sizes[size],
        fullWidth && "w-full",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
