import clsx from "clsx";
import { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
  error?: string;
}

export function Input({ className, icon, error, ...props }: InputProps) {
  return (
    <div className="w-full">
      <div className="relative">
        {icon && (
          <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none">
            {icon}
          </div>
        )}
        <input
          className={clsx(
            "w-full",
            "border border-gray-200/80 dark:border-navy-600/80",
            "rounded-[16px] bg-white dark:bg-navy-800",
            "text-gray-800 dark:text-white text-sm",
            "focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400",
            "placeholder:text-gray-400 dark:placeholder:text-gray-500",
            "transition-all duration-300",
            icon ? "pl-10 pr-4 py-2.5" : "px-4 py-2.5",
            error && "border-loss focus:border-loss focus:ring-loss/20",
            className
          )}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-1.5 text-xs text-loss">{error}</p>
      )}
    </div>
  );
}
