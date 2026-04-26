import React from 'react';

const JoineryView = ({ params }) => {
  const width = Number(params?.width || 1800);
  const isOversize = params?.is_oversize;
  const hasCentreSupport = params?.requires_centre_support;

  const railFixingCount = width >= 2400 ? 7 : width >= 1800 ? 5 : 4;
  const railEdgeOffset = 30;
  const railSpan = 300;
  const railSpacing = Math.round((railSpan - railEdgeOffset * 2) / Math.max(1, railFixingCount - 1));

  const topFixingCount = width >= 2400 ? 6 : width >= 1800 ? 4 : 3;
  const topEdgeOffset = 40;
  const topSpan = 400;
  const topSpacing = Math.round((topSpan - topEdgeOffset * 2) / Math.max(1, topFixingCount - 1));

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
          {Array.from({ length: railFixingCount }).map((_, i) => {
            const x = 140 + railEdgeOffset + i * railSpacing;
            return <circle key={i} cx={x} cy={190} r="4" fill="#ef4444" />;
          })}

          <text x="300" y="220" textAnchor="middle" fontSize="12">
            {railFixingCount} x screws | 5mm pilot | {railEdgeOffset}mm edge offset | {railSpacing}mm spacing
          </text>

          {/* Desktop */}
          <rect x="80" y="100" width="400" height="20" fill="#d6ad72" />

          {/* Top fixings - calculated spacing */}
          {Array.from({ length: topFixingCount }).map((_, i) => {
            const x = 80 + topEdgeOffset + i * topSpacing;
            return <circle key={i} cx={x} cy={110} r="4" fill="#2563eb" />;
          })}

          <text x="300" y="90" textAnchor="middle" fontSize="12">
            top fix from underside | {topFixingCount} x screws | {topEdgeOffset}mm edge offset | {topSpacing}mm spacing
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
