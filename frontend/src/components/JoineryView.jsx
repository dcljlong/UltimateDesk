import React, { useMemo, useState } from 'react';

const JoineryView = ({ params }) => {
  const width = Number(params?.width || 1800);
  const isOversize = params?.is_oversize;
  const hasCentreSupport = params?.requires_centre_support;

  const railFixingCount = width >= 2400 ? 7 : width >= 1800 ? 5 : 4;
  const railEdgeOffset = 30;
  const railSpan = width - 120; // 60mm clearance each side
  const railSpacing = Math.round((railSpan - railEdgeOffset * 2) / Math.max(1, railFixingCount - 1));

  const topFixingCount = width >= 2400 ? 6 : width >= 1800 ? 4 : 3;
  const topEdgeOffset = 40;
  const topSpan = width - 160; // 80mm inset from edges
  const topSpacing = Math.round((topSpan - topEdgeOffset * 2) / Math.max(1, topFixingCount - 1));

  const [joineryMethod, setJoineryMethod] = useState('screw');

  const joinerySpec = useMemo(() => {
    const methods = {
      screw: {
        label: 'Screw fixing',
        railLabel: `${railFixingCount} x screws | 5mm pilot | ${railEdgeOffset}mm edge offset | ${railSpacing}mm spacing`,
        topLabel: `top fix from underside | ${topFixingCount} x screws | ${topEdgeOffset}mm edge offset | ${topSpacing}mm spacing`,
        notes: [
          'Fastest prototype / DIY method.',
          'Pilot holes required before assembly.',
          'Use countersunk screws and confirm screw length against material thickness.',
        ],
        railColour: '#ef4444',
        topColour: '#2563eb',
      },
      confirmat: {
        label: 'Confirmat screw fixing',
        railLabel: `${railFixingCount} x confirmat screws | 7mm clearance | ${railEdgeOffset}mm edge offset | ${railSpacing}mm spacing`,
        topLabel: `top fix from underside | ${topFixingCount} x screws | ${topEdgeOffset}mm edge offset | ${topSpacing}mm spacing`,
        notes: [
          'Better flat-pack style fixing than standard wood screws.',
          'Requires correct stepped drill / confirmat bit.',
          'Check edge distance carefully on 18mm sheet material.',
        ],
        railColour: '#f97316',
        topColour: '#2563eb',
      },
      dowel: {
        label: 'Dowel alignment',
        railLabel: `${railFixingCount} x dowels | 8mm hole | ${railEdgeOffset}mm edge offset | ${railSpacing}mm spacing`,
        topLabel: `top alignment dowels | ${topFixingCount} x 8mm holes | ${topEdgeOffset}mm edge offset | ${topSpacing}mm spacing`,
        notes: [
          'Cleaner hidden fixing method.',
          'Needs accurate drilling and dry-fit check.',
          'Usually still needs glue, clamps, or secondary mechanical fixing.',
        ],
        railColour: '#16a34a',
        topColour: '#0891b2',
      },
      slot: {
        label: 'CNC slot/tab locating',
        railLabel: `${railFixingCount} locating tabs | 6mm cutter allowance | ${railEdgeOffset}mm edge offset | ${railSpacing}mm spacing`,
        topLabel: `underside locating pockets | ${topFixingCount} positions | ${topEdgeOffset}mm inset | ${topSpacing}mm spacing`,
        notes: [
          'Most CNC-native locating method.',
          'Requires pocket/slot CAM operations, not just profile cutting.',
          'Tab and pocket tolerances must be tested on the actual CNC and material.',
        ],
        railColour: '#9333ea',
        topColour: '#0f766e',
      },
    };
    return methods[joineryMethod] || methods.screw;
  }, [joineryMethod, railFixingCount, railEdgeOffset, railSpacing, topFixingCount, topEdgeOffset, topSpacing]);

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold">Joinery / Fixing View</h2>

      <div className="text-sm text-[var(--text-secondary)]">
        Shows how components are fixed together. This is the key layer for CNC and factory build.
      </div>

      <div className="neu-surface rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-sm font-bold">Joinery method</div>
          <div className="text-xs text-[var(--text-secondary)]">Changes fixing specs and manufacturing notes.</div>
        </div>
        <select
          value={joineryMethod}
          onChange={(e) => setJoineryMethod(e.target.value)}
          className="bg-[var(--surface-elevated)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
          data-testid="joinery-method-select"
        >
          <option value="screw">Screw fixing</option>
          <option value="confirmat">Confirmat screw fixing</option>
          <option value="dowel">Dowel alignment</option>
          <option value="slot">CNC slot/tab locating</option>
        </select>
      </div>

      <div className="bg-white rounded-xl p-4">
        <svg viewBox="0 0 800 400" className="w-full">

          {/* Leg */}
          <rect x="100" y="150" width="40" height="150" fill="#111827" />

          {/* Rail */}
          <rect x="140" y="180" width="300" height="20" fill="#111827" />

          {/* Rail fixings - calculated spacing */}
          {Array.from({ length: railFixingCount }).map((_, i) => {
            const x = 140 + railEdgeOffset + i * railSpacing;
            return <circle key={i} cx={x} cy={190} r="4" fill={joinerySpec.railColour} />;
          })}

          <text x="300" y="220" textAnchor="middle" fontSize="12">
            {joinerySpec.railLabel}
          </text>

          {/* Desktop */}
          <rect x="80" y="100" width="400" height="20" fill="#d6ad72" />

          {/* Top fixings - calculated spacing */}
          {Array.from({ length: topFixingCount }).map((_, i) => {
            const x = 80 + topEdgeOffset + i * topSpacing;
            return <circle key={i} cx={x} cy={110} r="4" fill={joinerySpec.topColour} />;
          })}

          <text x="300" y="90" textAnchor="middle" fontSize="12">
            {joinerySpec.topLabel}
          </text>

          {/* Centre support */}
          {hasCentreSupport && (
            <>
              <rect x="300" y="200" width="20" height="120" fill="#374151" />
              <text x="330" y="260" fontSize="12">centre support</text>
            </>
          )}

          {/* Split top */}
          {isOversize && (
            <>
              <line x1="280" y1="100" x2="280" y2="120" stroke="#ef4444" strokeWidth="3"/>
              <text x="280" y="80" textAnchor="middle" fontSize="12">
                split joint + plate
              </text>
            </>
          )}

        </svg>
      </div>

      <div className="text-sm text-[var(--text-secondary)]">
        Current method: <strong>{joinerySpec.label}</strong>
        <ul className="list-disc ml-5 mt-2">
          {joinerySpec.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
          <li>Split tops: join plate + alignment check required.</li>
          <li>Centre support: fixed to underside and checked against knee clearance.</li>
        </ul>
      </div>
    </div>
  );
};

export default JoineryView;
