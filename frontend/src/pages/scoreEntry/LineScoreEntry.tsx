interface LineScoreEntryProps {
  innings: number;
  awayName: string;
  homeName: string;
  awayRuns: number[];
  homeRuns: number[];
  awayE: number;
  homeE: number;
  awayLob: number;
  homeLob: number;
  onChange: (
    side: "home" | "away",
    field: "runs" | "e" | "lob",
    value: number,
    inningIndex?: number,
  ) => void;
}

export function LineScoreEntry({
  innings, awayName, homeName, awayRuns, homeRuns, awayE, homeE, awayLob, homeLob, onChange,
}: LineScoreEntryProps) {
  const inningNumbers = Array.from({ length: innings }, (_, i) => i + 1);

  return (
    <table className="score-entry-table">
      <thead>
        <tr>
          <th className="name-cell">局數</th>
          {inningNumbers.map((n) => (
            <th key={n}>{n}</th>
          ))}
          <th>E</th>
          <th>LOB</th>
        </tr>
      </thead>
      <tbody>
        <LineScoreRow
          name={awayName}
          side="away"
          runs={awayRuns}
          e={awayE}
          lob={awayLob}
          innings={innings}
          onChange={onChange}
        />
        <LineScoreRow
          name={homeName}
          side="home"
          runs={homeRuns}
          e={homeE}
          lob={homeLob}
          innings={innings}
          onChange={onChange}
        />
      </tbody>
    </table>
  );
}

function LineScoreRow({
  name, side, runs, e, lob, innings, onChange,
}: {
  name: string;
  side: "home" | "away";
  runs: number[];
  e: number;
  lob: number;
  innings: number;
  onChange: LineScoreEntryProps["onChange"];
}) {
  return (
    <tr>
      <td className="name-cell">{name}</td>
      {Array.from({ length: innings }, (_, i) => (
        <td key={i}>
          <input
            type="number"
            className="grid-cell"
            value={runs[i] ?? 0}
            onChange={(ev) => onChange(side, "runs", Number(ev.target.value) || 0, i)}
          />
        </td>
      ))}
      <td>
        <input
          type="number"
          className="grid-cell"
          value={e}
          onChange={(ev) => onChange(side, "e", Number(ev.target.value) || 0)}
        />
      </td>
      <td>
        <input
          type="number"
          className="grid-cell"
          value={lob}
          onChange={(ev) => onChange(side, "lob", Number(ev.target.value) || 0)}
        />
      </td>
    </tr>
  );
}
