import React from "react";
import Sidebar from "@/components/dashboard/Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-bg text-ink flex overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-x-hidden overflow-y-auto bg-bg">
        <div className="w-full max-w-[1240px] mx-auto p-6 lg:p-10">
          {children}
        </div>
      </main>
    </div>
  );
}
