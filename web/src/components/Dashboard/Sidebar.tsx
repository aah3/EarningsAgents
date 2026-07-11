"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  LayoutDashboard,
  TrendingUp,
  Layers,
  Calendar,
  History,
  Gauge,
  Settings,
} from "lucide-react";

const navItems = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { name: "History", href: "/dashboard/history", icon: History },
  { name: "Predictions", href: "/dashboard/predictions", icon: TrendingUp },
  { name: "Batch Analysis", href: "/dashboard/batch", icon: Layers },
  { name: "Calendar", href: "/dashboard/calendar", icon: Calendar },
  { name: "Performance", href: "/dashboard/performance", icon: Gauge },
  { name: "Settings", href: "/dashboard/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 h-screen w-[248px] max-[900px]:w-[72px] shrink-0 flex flex-col bg-panel border-r border-panel-line px-3.5 py-5 z-20 shadow-[4px_0_24px_rgba(0,0,0,0.3)] transition-all duration-300 overflow-hidden">
      {/* Top Header/Brand */}
      <div className="flex items-center gap-3 select-none pb-5 justify-start max-[900px]:justify-center">
        <Link
          href="/"
          className="brand flex items-center gap-3 font-display font-bold text-[19px] tracking-[-0.01em] text-white select-none focus-visible:ring-2 focus-visible:ring-teal outline-none rounded-lg"
        >
          <span
            className="logo w-[30px] h-[30px] rounded-[9px] bg-gradient-to-br from-teal to-teal-deep grid place-items-center text-[#04231F] font-bold flex-shrink-0"
            style={{ boxShadow: "0 0 22px rgba(45, 212, 191, 0.45)" }}
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
              <path d="M12 3l8 4.5-8 4.5-8-4.5L12 3z" fill="#04231F" />
              <path
                d="M4 12l8 4.5 8-4.5"
                stroke="#04231F"
                strokeWidth="1.6"
                fill="none"
              />
              <path
                d="M4 16.2l8 4.5 8-4.5"
                stroke="#04231F"
                strokeWidth="1.6"
                fill="none"
              />
            </svg>
          </span>
          <span className="max-[900px]:hidden font-display font-bold text-[19px] tracking-[-0.01em]">
            EarningsAI
          </span>
        </Link>
      </div>

      {/* Nav List */}
      <nav className="flex-1 flex flex-col gap-2.5 overflow-y-auto custom-scrollbar select-none py-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3.5 px-4 py-3 rounded-xl transition-all font-body font-semibold text-[14.5px] focus-visible:ring-2 focus-visible:ring-teal outline-none
                ${
                  isActive
                    ? "bg-teal/10 border-l-2 border-teal text-teal shadow-lg shadow-teal/5"
                    : "text-ink-mute border-l-2 border-transparent hover:bg-white/[0.03] hover:text-ink hover:translate-x-0.5"
                }`}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? "text-teal" : "text-ink-mute"}`} />
              <span className="max-[900px]:hidden truncate">{item.name}</span>
            </Link>
          );
        })}
      </nav>

    </aside>
  );
}
