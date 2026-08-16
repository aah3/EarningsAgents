import SiteNav from "@/components/marketing/SiteNav";
import Hero from "@/components/marketing/Hero";
import DataSources from "@/components/marketing/DataSources";
import HowItWorks from "@/components/marketing/HowItWorks";
import AgentRoster from "@/components/marketing/AgentRoster";
import TrackRecord from "@/components/marketing/TrackRecord";
import Faq from "@/components/marketing/Faq";
import CtaBand from "@/components/marketing/CtaBand";
import SiteFooter from "@/components/marketing/SiteFooter";

export default function Home() {
  return (
    <main className="min-h-screen bg-bg">
      <SiteNav />
      <Hero />
      <DataSources />
      <HowItWorks />
      <AgentRoster />
      <TrackRecord />
      <Faq />
      <CtaBand />
      <SiteFooter />
    </main>
  );
}
