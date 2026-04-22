import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Package, TreeStructure, Clock, CurrencyDollar } from '@phosphor-icons/react';

const SHEET_WIDTH = 2400;
const SHEET_HEIGHT = 1200;
const SCALE = 0.15;

const NestingViewer = ({ nestingData, cncOutput, className = '' }) => {
  const sheets = useMemo(() => {
    if (!nestingData?.parts) return [];

    const sheetMap = {};
    nestingData.parts.forEach((part) => {
      const sheetIdx = part.sheet || 0;
      if (!sheetMap[sheetIdx]) {
        sheetMap[sheetIdx] = [];
      }
      sheetMap[sheetIdx].push(part);
    });

    return Object.entries(sheetMap)
      .map(([idx, parts]) => ({
        index: parseInt(idx, 10),
        parts,
      }))
      .sort((a, b) => a.index - b.index);
  }, [nestingData]);

  const colors = [
    '#8E8E93', '#FF3B30', '#FF9500', '#FFCC00', '#34C759',
    '#007AFF', '#5856D6', '#AF52DE', '#A2845E', '#FF2D55'
  ];

  const getPartColor = (name) => {
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  if (!nestingData) {
    return (
      <div className={`flex items-center justify-center h-full text-[var(--text-secondary)] ${className}`}>
        <p>Cut layout is updating...</p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="neu-surface p-4 rounded-xl">
          <div className="flex items-center gap-2 text-[var(--text-secondary)] mb-1">
            <Package size={16} />
            <span className="text-xs">Sheets</span>
          </div>
          <p className="text-2xl font-bold font-mono">{nestingData.sheets_required}</p>
        </div>

        <div className="neu-surface p-4 rounded-xl">
          <div className="flex items-center gap-2 text-[var(--text-secondary)] mb-1">
            <TreeStructure size={16} />
            <span className="text-xs">Waste</span>
          </div>
          <p className={`text-2xl font-bold font-mono ${nestingData.waste_percentage < 5 ? 'text-[var(--success)]' : 'text-[var(--primary)]'}`}>
            {nestingData.waste_percentage}%
          </p>
        </div>

        <div className="neu-surface p-4 rounded-xl">
          <div className="flex items-center gap-2 text-[var(--text-secondary)] mb-1">
            <Package size={16} />
            <span className="text-xs">Parts</span>
          </div>
          <p className="text-2xl font-bold font-mono">{nestingData.parts.length}</p>
        </div>

        <div className="neu-surface p-4 rounded-xl">
          <div className="flex items-center gap-2 text-[var(--text-secondary)] mb-1">
            <Clock size={16} />
            <span className="text-xs">Cut Time</span>
          </div>
          <p className="text-2xl font-bold font-mono">{cncOutput ? `${Math.round(cncOutput.estimated_cut_time_minutes)}m` : '--'}</p>
        </div>

        <div className="neu-surface p-4 rounded-xl">
          <div className="flex items-center gap-2 text-[var(--text-secondary)] mb-1">
            <CurrencyDollar size={16} />
            <span className="text-xs">Material</span>
          </div>
          <p className="text-2xl font-bold font-mono">{cncOutput ? `$${cncOutput.material_cost_nzd}` : '--'}</p>
        </div>
      </div>

      <div className="space-y-4">
        {sheets.map((sheet) => (
          <motion.div
            key={sheet.index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: sheet.index * 0.1 }}
            className="neu-surface p-4 rounded-xl"
          >
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-bold">Sheet {sheet.index + 1}</h4>
              <span className="text-xs font-mono text-[var(--text-secondary)]">
                {SHEET_WIDTH}mm x {SHEET_HEIGHT}mm
              </span>
            </div>

            <div
              className="relative bg-[#D4A574] rounded-lg overflow-hidden mx-auto"
              style={{
                width: SHEET_WIDTH * SCALE,
                height: SHEET_HEIGHT * SCALE,
              }}
            >
              <div
                className="absolute inset-0 opacity-30"
                style={{
                  backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(139,90,43,0.3) 2px, rgba(139,90,43,0.3) 4px)'
                }}
              />

              {sheet.parts.map((part, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: idx * 0.05 }}
                  className="absolute border-2 border-black/30 rounded-sm flex items-center justify-center overflow-hidden group"
                  style={{
                    left: part.x * SCALE,
                    top: part.y * SCALE,
                    width: part.width * SCALE,
                    height: part.height * SCALE,
                    backgroundColor: getPartColor(part.name),
                  }}
                  title={`${part.name}: ${part.width}mm x ${part.height}mm${part.rotated ? ' (rotated)' : ''}`}
                >
                  {part.width * SCALE > 40 && part.height * SCALE > 18 && (
                    <span className="text-[8px] font-mono text-white text-center px-1 truncate">
                      {part.name}
                    </span>
                  )}
                </motion.div>
              ))}
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="text-left border-b border-[var(--border)]">
                    <th className="py-2 pr-3">Part</th>
                    <th className="py-2 pr-3">Size</th>
                    <th className="py-2 pr-3">Rotated</th>
                  </tr>
                </thead>
                <tbody>
                  {sheet.parts.map((part, idx) => (
                    <tr key={idx} className="border-b border-[var(--border)]/60">
                      <td className="py-2 pr-3 font-mono">{part.name}</td>
                      <td className="py-2 pr-3 font-mono">{part.width} x {part.height}</td>
                      <td className="py-2 pr-3 font-mono">{part.rotated ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default NestingViewer;
