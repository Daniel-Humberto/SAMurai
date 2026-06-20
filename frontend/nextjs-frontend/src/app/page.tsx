import { ModeSelector } from "./components/ModeSelector";
import { SamuraiHero } from "./components/SamuraiHero";
import { GlobalHeader } from "./components/GlobalHeader";

export default function Home() {
  return (
    <main className="flex min-h-screen w-full flex-col gap-10 px-6 pt-8 pb-0 md:px-10 md:pt-10 md:pb-0">
      <GlobalHeader />

      <ModeSelector />

      <SamuraiHero />
    </main>
  );
}


