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
    { name: "Settings", href: "/dashboard/settings", icon: "⚙️" },
];

export default function Sidebar() {
    const pathname = usePathname();
    const { user } = useUser();

    return (
        <aside className="w-64 border-r border-white/5 bg-[#080b11] flex-shrink-0 flex flex-col h-screen sticky top-0 z-20">
            <div className="p-8 border-b border-white/5 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center shadow-[0_0_15px_rgba(45,212,191,0.5)]">
                    <svg className="w-5 h-5 text-background" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                </div>
                <span className="text-xl font-black tracking-tighter uppercase text-white shadow-black">Earnings AI</span>
            </div>

            <nav className="flex-1 p-4 space-y-2 mt-2">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-4 px-4 py-3.5 rounded-xl transition-all font-bold text-sm ${isActive
                                ? "bg-accent/10 border border-accent/20 text-accent shadow-lg shadow-accent/5"
                                : "text-gray-400 border border-transparent hover:bg-white/5 hover:text-white"
                                }`}
                        >
                            <span className="text-xl">{item.icon}</span>
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-4 border-t border-white/5 bg-black/20">
                <div className="flex items-center justify-between p-3 rounded-2xl border border-white/5 bg-white/[0.02]">
                    <div className="flex items-center gap-3 min-w-0">
                        <UserButton afterSignOutUrl="/" />
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-bold text-white truncate">{user?.firstName || "User Profile"}</p>
                            <p className="text-[10px] text-accent font-medium truncate uppercase tracking-widest mt-0.5">Pro Member</p>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
