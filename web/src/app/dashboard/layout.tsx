import React from "react";
import Sidebar from "@/components/dashboard/Sidebar";
import DisclaimerBanner from "@/components/dashboard/DisclaimerBanner";
import FeedbackWidget from "@/components/dashboard/FeedbackWidget";
import { SignedIn, UserButton } from "@clerk/nextjs";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-bg text-ink flex overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-x-hidden overflow-y-auto bg-bg">
        <div className="w-full max-w-[1240px] mx-auto p-6 lg:p-10 flex flex-col gap-6">
          <div className="flex justify-between items-center w-full gap-4">
            <DisclaimerBanner />
            <SignedIn>
              <UserButton afterSignOutUrl="/" />
            </SignedIn>
          </div>
          {children}
        </div>
      </main>
      <FeedbackWidget />
    </div>
  );
}
