"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { UserButton, useUser } from "@clerk/nextjs";

const navItems = [
    { name: "Overview", href: "/dashboard", icon: "📊" },
    { name: "Predictions", href: "/dashboard/predictions", icon: "📈" },
    { name: "Batch Analysis", href: "/dashboard/batch", icon: "⚡" },
    { name: "Calendar", href: "/dashboard/calendar", icon: "📅" },
    { name: "History", href: "/dashboard/history", icon: "📜" },
    { name: "Performance", href: "/dashboard/performance", icon: "🎯" },
    { name: "Settings", href: "/dashboard/settings", icon: "⚙️" },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { user } = useUser();

    return (
        <aside className="w-72 border-r border-white/5 bg-[#080b11] flex-shrink-0 flex flex-col h-screen sticky top-0 z-20 shadow-[4px_0_24px_rgba(0,0,0,0.2)]">
            <div className="p-8 border-b border-white/5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent flex items-center justify-center shadow-[0_0_20px_rgba(45,212,191,0.4)]">
                    <svg className="w-6 h-6 text-background" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                </div>
                <span className="text-2xl font-black tracking-tighter uppercase text-white shadow-black">Earnings AI</span>
            </div>

            <nav className="flex-1 px-4 py-8 space-y-3 overflow-y-auto custom-scrollbar">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-5 px-5 py-4 rounded-2xl transition-all font-bold text-[15px] ${isActive
                                ? "bg-accent/10 border border-accent/20 text-accent shadow-lg shadow-accent/5 translate-x-1"
                                : "text-gray-400 border border-transparent hover:bg-white/5 hover:text-white hover:translate-x-1"
                                }`}
                        >
                            <span className="text-2xl">{item.icon}</span>
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-6 border-t border-white/5 bg-black/20">
                <div className="flex items-center justify-between p-4 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors cursor-pointer">
                    <div className="flex items-center gap-4 min-w-0">
                        <UserButton afterSignOutUrl="/" appearance={{ elements: { avatarBox: "w-10 h-10" } }} />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-bold text-white truncate">{user?.firstName || "User Profile"}</p>
                            <p className="text-[11px] text-accent font-black truncate uppercase tracking-widest mt-1">Pro Member</p>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
