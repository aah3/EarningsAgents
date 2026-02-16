import Sidebar from "@/components/Dashboard/Sidebar";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-background text-foreground flex">
            <Sidebar />
            <main className="flex-1 ml-64 p-12 overflow-y-auto">
                {children}
            </main>
        </div>
    );
}
