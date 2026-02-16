import Navbar from "@/components/Landing/Navbar";
import HeroSection from "@/components/Landing/HeroSection";
import AgentCommittee from "@/components/Landing/AgentCommittee";
import LivePreview from "@/components/Landing/LivePreview";
import DataSources from "@/components/Landing/DataSources";
import Footer from "@/components/Landing/Footer";

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <HeroSection />
      <AgentCommittee />
      <LivePreview />
      <DataSources />
      <Footer />
    </main>
  );
}
