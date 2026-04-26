import React from 'react';

const labelStyle = {
  fontSize: 11,
  fill: 'currentColor',
  fontWeight: 700,
};

const dimStyle = {
  fontSize: 10,
  fill: 'currentColor',
  opacity: 0.8,
};

const BuildViews2D = ({ params }) => {
  const width = Number(params.width || 1800);
  const depth = Number(params.depth || 800);
  const height = Number(params.height || 750);
  const thickness = Number(params.material_thickness || 18);
  const isOversize = Boolean(params.is_oversize) || width > 2400;
  const splitCount = isOversize ? Number(params.desktop_split_count || 2) : 1;
  const hasCentreSupport = Boolean(params.requires_centre_support) || isOversize;

  const topScale = Math.min(720 / width, 260 / depth);
  const topW = width * topScale;
  const topD = depth * topScale;
  const topX = (780 - topW) / 2;
  const topY = 60;

  const frontScale = Math.min(720 / width, 220 / height);
  const frontW = width * frontScale;
  const frontH = height * frontScale;
  const frontX = (780 - frontW) / 2;
  const frontY = 285;

  const sideScale = Math.min(360 / depth, 220 / height);
  const sideW = depth * sideScale;
  const sideH = height * sideScale;
  const sideX = 210;
  const sideY = 285;

  const panelClass = "rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm";
  const titleClass = "text-sm font-bold mb-1";
  const subClass = "text-xs text-[var(--text-secondary)] mb-3";

  return (
    <div className="h-[calc(100vh-128px)] overflow-y-auto p-4 pb-24">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold">2D Build Views</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Plan, user-side, and side views for checking desk logic before export.
          </p>
        </div>

        {isOversize && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm">
            <span className="font-bold text-amber-300">Oversize split desk:</span>{' '}
            {splitCount} desktop panels with centre support.
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className={panelClass}>
          <div className={titleClass}>Top plan view</div>
          <div className={subClass}>Shows split line, user/sitting side, rear cable side, centre support, and knee clearance zone.</div>

          <svg viewBox="0 0 780 380" className="w-full rounded-xl bg-white text-slate-900">
            <rect x={topX} y={topY} width={topW} height={topD} fill="#d7b07a" stroke="#111827" strokeWidth="2" />

            {isOversize && (
              <>
                <line
                  x1={topX + topW / 2}
                  y1={topY}
                  x2={topX + topW / 2}
                  y2={topY + topD}
                  stroke="#ef4444"
                  strokeWidth="4"
                />
                <rect
                  x={topX + topW / 2 - 18}
                  y={topY + topD * 0.24 - 44}
                  width="36"
                  height="88"
                  fill="rgba(17,24,39,0.16)"
                  stroke="#111827"
                  strokeWidth="1"
                />
                <rect
                  x={topX + 24}
                  y={topY + topD * 0.58}
                  width={topW - 48}
                  height={topD * 0.30}
                  fill="rgba(34,197,94,0.10)"
                  stroke="rgba(34,197,94,0.55)"
                  strokeDasharray="8 6"
                  strokeWidth="2"
                />
                <text x={topX + topW / 2} y={topY + topD * 0.75} textAnchor="middle" style={labelStyle}>
                  knee clearance / sitting zone
                </text>
                <text x={topX + topW / 2 + 26} y={topY + topD * 0.24} style={labelStyle}>
                  centre support set back
                </text>
              </>
            )}

            <text x={390} y={30} textAnchor="middle" style={labelStyle}>
              TOP PLAN
            </text>
            <text x={390} y={topY - 14} textAnchor="middle" style={labelStyle}>
              REAR / CABLE TRAY SIDE
            </text>
            <text x={390} y={topY + topD + 58} textAnchor="middle" style={labelStyle}>
              USER SIDE / SITTING SIDE
            </text>
            <text x={390} y={topY + topD + 34} textAnchor="middle" style={dimStyle}>
              Overall width: {width}mm
            </text>
            <text x={topX + topW + 18} y={topY + topD / 2} style={dimStyle} transform={`rotate(90 ${topX + topW + 18} ${topY + topD / 2})`}>
              Depth: {depth}mm
            </text>

            {isOversize && (
              <>
                <text x={topX + topW * 0.25} y={topY + topD / 2} textAnchor="middle" style={labelStyle}>
                  Left panel ~{Math.ceil(width / 2)}mm
                </text>
                <text x={topX + topW * 0.75} y={topY + topD / 2} textAnchor="middle" style={labelStyle}>
                  Right panel ~{Math.floor(width / 2)}mm
                </text>
              </>
            )}
          </svg>
        </div>

        <div className={panelClass}>
          <div className={titleClass}>Build summary</div>
          <div className={subClass}>Quick manufacturing logic check.</div>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-xl bg-[var(--surface-elevated)] p-3">
              <div className="text-[var(--text-secondary)] text-xs">Overall size</div>
              <div className="font-mono font-bold">{width} × {depth} × {height}mm</div>
            </div>
            <div className="rounded-xl bg-[var(--surface-elevated)] p-3">
              <div className="text-[var(--text-secondary)] text-xs">Material</div>
              <div className="font-mono font-bold">{thickness}mm plywood</div>
            </div>
            <div className="rounded-xl bg-[var(--surface-elevated)] p-3">
              <div className="text-[var(--text-secondary)] text-xs">Desktop</div>
              <div className="font-mono font-bold">{splitCount} panel{splitCount === 1 ? '' : 's'}</div>
            </div>
            <div className="rounded-xl bg-[var(--surface-elevated)] p-3">
              <div className="text-[var(--text-secondary)] text-xs">Centre support</div>
              <div className="font-mono font-bold">{hasCentreSupport ? 'Required' : 'Not required'}</div>
            </div>
          </div>

          <div className="mt-4 rounded-xl border border-[var(--border)] p-3 text-xs text-[var(--text-secondary)]">
            User side is the open sitting edge. Rear side is the cable tray/service side. Centre support is shown set back toward the rear to preserve knee clearance. Final dimensions, joinery, tooling, feeds, hold-down, and CAM setup must still be checked before cutting.
          </div>
        </div>

        <div className={panelClass}>
          <div className={titleClass}>User-side elevation</div>
          <div className={subClass}>Shows the open sitting side and knee zone. Centre support is rear-set and should not block the user's knees.</div>

          <svg viewBox="0 0 780 420" className="w-full rounded-xl bg-white text-slate-900">
            <line x1="70" y1="360" x2="710" y2="360" stroke="#cbd5e1" strokeWidth="2" />

            <rect x={frontX} y={frontY - frontH} width={frontW} height="10" fill="#111827" />
            <rect x={frontX + 45} y={frontY - frontH + 10} width="12" height={frontH - 10} fill="#111827" />
            <rect x={frontX + frontW - 57} y={frontY - frontH + 10} width="12" height={frontH - 10} fill="#111827" />
            <rect x={frontX + 75} y={frontY - frontH + frontH * 0.52} width={frontW - 150} height="18" fill="#111827" />
            <rect
              x={frontX + 92}
              y={frontY - frontH + frontH * 0.28}
              width={frontW - 184}
              height={frontH * 0.52}
              fill="rgba(34,197,94,0.08)"
              stroke="rgba(34,197,94,0.45)"
              strokeDasharray="8 6"
              strokeWidth="2"
            />
            <text x={frontX + frontW / 2} y={frontY - frontH + frontH * 0.42} textAnchor="middle" style={labelStyle}>
              open knee zone
            </text>
            <rect x={frontX + 110} y={frontY - frontH + frontH * 0.62} width={frontW - 220} height="56" fill="#1f2937" />

            {hasCentreSupport && (
              <>
                <rect
                  x={frontX + frontW / 2 - 5}
                  y={frontY - frontH + 28}
                  width="10"
                  height={frontH - 54}
                  fill="rgba(17,24,39,0.38)"
                  stroke="#111827"
                  strokeDasharray="7 5"
                  strokeWidth="2"
                />
                <rect
                  x={frontX + frontW / 2 - 44}
                  y={frontY - 24}
                  width="88"
                  height="10"
                  fill="rgba(17,24,39,0.38)"
                  stroke="#111827"
                  strokeDasharray="7 5"
                  strokeWidth="2"
                />
                <text x={frontX + frontW / 2 + 18} y={frontY - frontH + 52} style={dimStyle}>
                  rear-set support
                </text>
              </>
            )}

            {isOversize && (
              <line
                x1={frontX + frontW / 2}
                y1={frontY - frontH - 8}
                x2={frontX + frontW / 2}
                y2={frontY - frontH + 32}
                stroke="#ef4444"
                strokeWidth="4"
              />
            )}

            <text x="390" y="34" textAnchor="middle" style={labelStyle}>USER-SIDE ELEVATION</text>
            <text x="390" y="390" textAnchor="middle" style={dimStyle}>Width: {width}mm</text>
            <text x="390" y="374" textAnchor="middle" style={labelStyle}>OPEN USER / SITTING SIDE - CENTRE SUPPORT SET BACK</text>
            <text x={frontX + frontW + 24} y={frontY - frontH / 2} style={dimStyle} transform={`rotate(90 ${frontX + frontW + 24} ${frontY - frontH / 2})`}>
              Height: {height}mm
            </text>
          </svg>
        </div>

        <div className={panelClass}>
          <div className={titleClass}>Side elevation</div>
          <div className={subClass}>Shows depth, height, side rails, and desktop thickness.</div>

          <svg viewBox="0 0 780 420" className="w-full rounded-xl bg-white text-slate-900">
            <line x1="70" y1="360" x2="710" y2="360" stroke="#cbd5e1" strokeWidth="2" />

            <rect x={sideX} y={sideY - sideH} width={sideW} height="10" fill="#111827" />
            <rect x={sideX + 22} y={sideY - sideH + 10} width="12" height={sideH - 10} fill="#111827" />
            <rect x={sideX + sideW - 34} y={sideY - sideH + 10} width="12" height={sideH - 10} fill="#111827" />
            <rect x={sideX + 35} y={sideY - sideH + sideH * 0.58} width={sideW - 70} height="16" fill="#111827" />

            <text x="390" y="34" textAnchor="middle" style={labelStyle}>SIDE ELEVATION</text>
            <text x={sideX + sideW / 2} y="390" textAnchor="middle" style={dimStyle}>Depth: {depth}mm</text>
            <text x={sideX + sideW + 28} y={sideY - sideH / 2} style={dimStyle} transform={`rotate(90 ${sideX + sideW + 28} ${sideY - sideH / 2})`}>
              Height: {height}mm
            </text>
          </svg>
        </div>
      </div>
    </div>
  );
};

export default BuildViews2D;
