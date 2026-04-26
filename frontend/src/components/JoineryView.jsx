import React from 'react';

const JoineryView = ({ params }) => {
  const isOversize = params?.is_oversize;
  const hasCentreSupport = params?.requires_centre_support;

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold">Joinery / Fixing View</h2>

      <div className="text-sm text-[var(--text-secondary)]">
        Shows how components are fixed together. This is the key layer for CNC and factory build.
      </div>

      <div className="bg-white rounded-xl p-4">
        <svg viewBox="0 0 800 400" className="w-full">

          {/* Leg */}
          <rect x="100" y="150" width="40" height="150" fill="#111827" />

          {/* Rail */}
          <rect x="140" y="180" width="300" height="20" fill="#111827" />

          {/* Rail fixings - calculated spacing */}
          {Array.from({ length: 5 }).map((_, i) => {
            const edgeOffset = 30;
            const spacing = (300 - edgeOffset * 2) / 4;
            const x = 140 + edgeOffset + i * spacing;
            return <circle key={i} cx={x} cy={190} r="4" fill="#ef4444" />;
          })}

          <text x="300" y="220" textAnchor="middle" fontSize="12">
            5 x screws | 5mm pilot | 30mm edge offset | even spacing
          </text>

          {/* Desktop */}
          <rect x="80" y="100" width="400" height="20" fill="#d6ad72" />

          {/* Top fixings - calculated spacing */}
          {Array.from({ length: 4 }).map((_, i) => {
            const edgeOffset = 40;
            const spacing = (400 - edgeOffset * 2) / 3;
            const x = 80 + edgeOffset + i * spacing;
            return <circle key={i} cx={x} cy={110} r="4" fill="#2563eb" />;
          })}

          <text x="300" y="90" textAnchor="middle" fontSize="12">
            top fix from underside | 4 x screws | 40mm edge offset
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
        Typical logic:
        <ul className="list-disc ml-5 mt-2">
          <li>Rails to legs: screws or dowels</li>
          <li>Top to frame: underside screws</li>
          <li>Split tops: join plate + alignment</li>
          <li>Centre support: fixed to underside + floor</li>
        </ul>
      </div>
    </div>
  );
};

export default JoineryView;
