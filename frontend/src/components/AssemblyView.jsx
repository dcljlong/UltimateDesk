import React from 'react';

const AssemblyView = ({ params }) => {
  const width = Number(params?.width || 1800);
  const depth = Number(params?.depth || 800);
  const height = Number(params?.height || 750);
  const isOversize = Boolean(params?.is_oversize || width > 2400);
  const hasCentreSupport = Boolean(params?.requires_centre_support || isOversize);
  const hasCableTray = Boolean(params?.has_cable_management);
  const hasHeadsetHook = Boolean(params?.has_headset_hook);

  const partRows = [
    ['Desktop top', isOversize ? '2 panels, left + right' : '1 panel', 'Sits on frame. User side must face open knee zone.'],
    ['Leg posts', '4 posts', 'Front/rear corner supports.'],
    ['Rear upper rail', isOversize ? 'Split left + right' : '1 rail', 'Rear/service side rail under the back edge.'],
    ['Front lower rail', isOversize ? 'Split left + right' : '1 rail', 'Low front rail. Keep user-side knee clearance open.'],
    ['Back modesty panel', '1 panel', 'Rear/service side panel. Do not place on sitting side.'],
    ['Cable tray', hasCableTray ? 'Base, front, back, ends' : 'Not selected', 'Rear/service side only.'],
    ['Desktop centre join plate', isOversize ? 'Required' : 'Not required', 'Joins split top panels from underside.'],
    ['Centre support', hasCentreSupport ? 'Post, foot, under-top rail' : 'Not required', 'Set back toward rear/service side, not at front knee edge.'],
    ['Headset hook', hasHeadsetHook ? 'Backplate + arm' : 'Not selected', 'Accessory part. Position to suit user preference.'],
  ];

  return (
    <div className="h-[calc(100vh-170px)] overflow-y-auto p-4 pb-24 space-y-4" data-testid="assembly-view">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Assembly / Joinery View</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Reference assembly logic for checking how the desk goes together before export or manufacture.
          </p>
        </div>

        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
          Reference only - verify joinery, fixing, tooling, and CAM setup before cutting.
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="neu-surface rounded-2xl p-4">
          <h3 className="font-bold mb-1">Orientation</h3>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            User sits at the open side. Cable tray, modesty panel, and centre support are treated as rear/service-side items.
          </p>

          <div className="bg-white rounded-xl p-4 overflow-auto">
            <svg viewBox="0 0 860 520" className="w-full min-w-[680px]">
              <defs>
                <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
                  <path d="M0,0 L0,6 L8,3 z" fill="#111827" />
                </marker>
              </defs>

              <text x="430" y="28" textAnchor="middle" fontSize="16" fontWeight="800" fill="#111827">
                EXPLODED ASSEMBLY LOGIC
              </text>

              <text x="430" y="62" textAnchor="middle" fontSize="13" fontWeight="700" fill="#111827">
                REAR / CABLE TRAY SIDE
              </text>

              <rect x="140" y="95" width="580" height="105" rx="4" fill="#d6ad72" stroke="#111827" strokeWidth="3" />
              {isOversize && (
                <>
                  <line x1="430" y1="95" x2="430" y2="200" stroke="#ef4444" strokeWidth="5" />
                  <text x="290" y="154" textAnchor="middle" fontSize="13" fontWeight="700" fill="#111827">left top panel</text>
                  <text x="570" y="154" textAnchor="middle" fontSize="13" fontWeight="700" fill="#111827">right top panel</text>
                  <rect x="405" y="210" width="50" height="82" fill="rgba(17,24,39,0.16)" stroke="#111827" strokeWidth="2" />
                  <text x="490" y="255" fontSize="12" fontWeight="700" fill="#111827">underside centre join plate</text>
                </>
              )}

              <rect x="170" y="330" width="34" height="128" fill="#111827" />
              <rect x="656" y="330" width="34" height="128" fill="#111827" />
              <rect x="170" y="245" width="34" height="84" fill="#111827" opacity="0.55" />
              <rect x="656" y="245" width="34" height="84" fill="#111827" opacity="0.55" />

              <rect x="230" y="316" width="400" height="24" fill="#111827" />
              <text x="430" y="309" textAnchor="middle" fontSize="12" fontWeight="700" fill="#111827">rear upper rail / service-side frame</text>

              <rect x="255" y="370" width="350" height="76" fill="#1f2937" />
              <text x="430" y="414" textAnchor="middle" fontSize="12" fontWeight="700" fill="#ffffff">rear modesty panel</text>

              {hasCableTray && (
                <>
                  <rect x="255" y="282" width="350" height="18" fill="#374151" />
                  <text x="430" y="278" textAnchor="middle" fontSize="12" fontWeight="700" fill="#111827">cable tray behind user side</text>
                </>
              )}

              {hasCentreSupport && (
                <>
                  <rect x="421" y="300" width="18" height="145" fill="rgba(17,24,39,0.45)" stroke="#111827" strokeDasharray="7 5" strokeWidth="2" />
                  <rect x="386" y="450" width="88" height="14" fill="rgba(17,24,39,0.45)" stroke="#111827" strokeDasharray="7 5" strokeWidth="2" />
                  <text x="475" y="354" fontSize="12" fontWeight="700" fill="#111827">rear-set centre support</text>
                </>
              )}

              <rect x="180" y="468" width="500" height="28" fill="rgba(34,197,94,0.10)" stroke="rgba(34,197,94,0.65)" strokeDasharray="8 6" strokeWidth="2" />
              <text x="430" y="487" textAnchor="middle" fontSize="13" fontWeight="800" fill="#111827">
                OPEN USER / SITTING SIDE - KNEE ZONE
              </text>

              <line x1="430" y1="75" x2="430" y2="92" stroke="#111827" strokeWidth="2" markerEnd="url(#arrow)" />
              <line x1="430" y1="466" x2="430" y2="448" stroke="#111827" strokeWidth="2" markerEnd="url(#arrow)" />
            </svg>
          </div>
        </div>

        <div className="neu-surface rounded-2xl p-4">
          <h3 className="font-bold mb-1">Assembly order</h3>
          <p className="text-sm text-[var(--text-secondary)] mb-4">
            Simple build sequence for understanding the frame before making the files.
          </p>

          <ol className="space-y-3 text-sm">
            <li className="rounded-xl bg-[var(--surface-elevated)] p-3">
              <strong>1. Build the side frames</strong>
              <div className="text-[var(--text-secondary)]">Assemble legs and side rails square and level.</div>
            </li>
            <li className="rounded-xl bg-[var(--surface-elevated)] p-3">
              <strong>2. Add rear/service-side rails</strong>
              <div className="text-[var(--text-secondary)]">Rear upper rail and modesty panel go on the cable tray side.</div>
            </li>
            <li className="rounded-xl bg-[var(--surface-elevated)] p-3">
              <strong>3. Add front lower rail</strong>
              <div className="text-[var(--text-secondary)]">Keep the main sitting edge open for knee clearance.</div>
            </li>
            {hasCentreSupport && (
              <li className="rounded-xl bg-[var(--surface-elevated)] p-3">
                <strong>4. Fit rear-set centre support</strong>
                <div className="text-[var(--text-secondary)]">Set back toward the rear/service side to support the split top without blocking knees.</div>
              </li>
            )}
            {isOversize && (
              <li className="rounded-xl bg-[var(--surface-elevated)] p-3">
                <strong>{hasCentreSupport ? '5' : '4'}. Join split desktop panels</strong>
                <div className="text-[var(--text-secondary)]">Use the centre join plate underneath the split line. Verify fixing method before manufacture.</div>
              </li>
            )}
            <li className="rounded-xl bg-[var(--surface-elevated)] p-3">
              <strong>{isOversize ? (hasCentreSupport ? '6' : '5') : (hasCentreSupport ? '5' : '4')}. Fit accessories</strong>
              <div className="text-[var(--text-secondary)]">Cable tray, headset hook, and other accessories to suit final user position.</div>
            </li>
          </ol>
        </div>
      </div>

      <div className="neu-surface rounded-2xl p-4">
        <h3 className="font-bold mb-3">Part location guide</h3>
        <div className="overflow-auto">
          <table className="w-full text-sm min-w-[720px]">
            <thead>
              <tr className="text-left text-[var(--text-secondary)] border-b border-[var(--border)]">
                <th className="py-2 pr-3">Part group</th>
                <th className="py-2 pr-3">Required</th>
                <th className="py-2 pr-3">Where it goes</th>
              </tr>
            </thead>
            <tbody>
              {partRows.map(([group, required, location]) => (
                <tr key={group} className="border-b border-[var(--border)]">
                  <td className="py-2 pr-3 font-bold">{group}</td>
                  <td className="py-2 pr-3">{required}</td>
                  <td className="py-2 pr-3 text-[var(--text-secondary)]">{location}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-[var(--text-secondary)]">
        This is an assembly reference view only. It does not replace a joinery drawing, engineering review,
        CAM verification, tooling setup, feed/speed check, hold-down plan, or factory approval.
      </div>
    </div>
  );
};

export default AssemblyView;
