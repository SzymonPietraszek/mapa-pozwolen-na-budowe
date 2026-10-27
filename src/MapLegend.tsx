export default function MapLegend() {
  const periods = [
    { color: "#b3d9ff", label: "I połowa 2025" },
    { color: "#66a3e0", label: "II połowa 2025" },
    { color: "#3378bd", label: "I połowa 2026" },
    { color: "#174578", label: "II połowa 2026" },
    { color: "#d97706", label: "Brak daty / inny okres" },
  ];

  const types = [
    { color: "#16a34a", label: "Zabudowa jednorodzinna" },
    { color: "#dc2626", label: "Zabudowa wielorodzinna" },
    { color: "#1763bb", label: "Pozostałe" },
  ];

  return (
    <div
      style={{
        position: "absolute",
        zIndex: 1,
        right: 12,
        bottom: 24,
        padding: 9,
        background: "white",
        borderRadius: 6,
        boxShadow: "0 1px 4px rgba(0,0,0,0.25)",
        fontSize: 11,
        maxWidth: 190,
        color: "#222",
      }}
    >
      <strong>Data decyzji</strong>

      {periods.map((item) => (
        <div
          key={item.label}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 7,
          }}
        >
          <span
            style={{
              width: 18,
              height: 18,
              flexShrink: 0,
              background: item.color,
              border: "1px solid #777",
              borderRadius: 2,
            }}
          />
          <span>{item.label}</span>
        </div>
      ))}

      <div
        style={{
          borderTop: "1px solid #ddd",
          marginTop: 12,
          paddingTop: 10,
        }}
      >
        <strong>Rodzaj zabudowy — obrys</strong>

        {types.map((item) => (
          <div
            key={item.label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginTop: 7,
            }}
          >
            <span
              style={{
                width: 22,
                height: 0,
                flexShrink: 0,
                borderTop: `3px solid ${item.color}`,
              }}
            />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
