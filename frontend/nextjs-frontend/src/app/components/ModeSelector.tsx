import Link from "next/link";

const modes = [
  {
    href: "/live/setup",
    title: "Live",
    subtitle: "Camara o RTSP",
    description:
      "Inicia una sesion con stream en vivo, overlay tactico y narracion continua.",
  },
  {
    href: "/video/setup",
    title: "Video",
    subtitle: "MP4 o MOV",
    description:
      "Procesa partidos grabados, calibra homografia y genera informe ejecutivo.",
  },
  {
    href: "/history",
    title: "Historial",
    subtitle: "Casos guardados",
    description:
      "Consulta sesiones completadas, reportes PDF y metrica comparativa.",
  },
];

export function ModeSelector() {
  return (
    <section className="grid gap-5 lg:grid-cols-3">
      {modes.map((mode) => (
        <Link
          key={mode.title}
          href={mode.href}
          className="group rounded-[1.75rem] border border-slate-800 bg-slate-950/70 p-6 shadow-[0_24px_70px_rgba(2,6,23,0.38)] transition duration-300 hover:-translate-y-1 hover:border-amber-300 hover:shadow-[0_34px_100px_rgba(2,6,23,0.5)]"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-4xl uppercase text-slate-100">
                {mode.title}
              </h2>
              <span className="rounded-full bg-slate-950 px-3 py-1 text-xs uppercase tracking-[0.3em] text-white group-hover:bg-amber-400 group-hover:text-slate-950">
                Entrar
              </span>
            </div>
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-slate-400">
              {mode.subtitle}
            </p>
            <p className="text-sm leading-7 text-slate-300">{mode.description}</p>
          </div>
        </Link>
      ))}
    </section>
  );
}
