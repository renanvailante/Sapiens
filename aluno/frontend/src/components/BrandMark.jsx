// Símbolo "Constelação-S" da identidade Sapiens — traço em S com um nó de
// destaque (var(--brand-accent)). `tone="light"` usa branco para uso sobre
// fundos azuis/escuros; `tone="dark"` usa a navy da marca para uso sobre
// fundos claros.
export default function BrandMark({ className = "w-7 h-7", tone = "light" }) {
  const strokeColor = tone === "dark" ? "#132D5C" : "#ffffff";
  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden="true">
      <path
        d="M70,26 C70,26 40,26 40,42 C40,54 60,50 60,64 C60,78 30,78 30,78"
        fill="none"
        stroke={strokeColor}
        strokeWidth="4.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="40" cy="42" r="7" fill={strokeColor} />
      <circle cx="60" cy="64" r="6" fill={strokeColor} />
      <circle cx="30" cy="78" r="5.5" fill={strokeColor} />
      <circle cx="70" cy="26" r="11" fill="#4A85E3" />
    </svg>
  );
}
