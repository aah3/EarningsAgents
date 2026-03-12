import Sidebar from "@/components/Dashboard/Sidebar";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-background text-foreground flex overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-x-hidden overflow-y-auto">
                <div className="w-full max-w-7xl mx-auto p-6 lg:p-10">
                    {children}
                </div>
            </main>
        </div>
    );
}
