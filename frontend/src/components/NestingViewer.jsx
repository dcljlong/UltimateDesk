import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Package, TreeStructure, Clock, CurrencyDollar } from '@phosphor-icons/react';

const SHEET_WIDTH = 2400;
const SHEET_HEIGHT = 1200;
const SCALE = 0.15; // Scale for visualization

const NestingViewer = ({ nestingData, cncOutput, className = '' }) => {
  const sheets = useMemo(() => {
    if (!nestingData?.parts) return [];
    
    // Group parts by sheet
    const sheetMap = {};
    nestingData.parts.forEach(part => {
      const sheetIdx = part.sheet || 0;
      if (!sheetMap[sheetIdx]) {
        sheetMap[sheetIdx] = [];
      }
      sheetMap[sheetIdx].push(part);
    });
    
    return Object.entries(sheetMap).map(([idx, parts]) => ({
      index: parseInt(idx),
      parts
    }));
  }, [nestingData]);

  // Color palette for parts
  const colors = [
    '#FF3B30', '#FF9500', '#FFCC00', '#34C759', '#007AFF',
    '#5856D6', '#AF52DE', '#FF2D55', '#A2845E', '#8E8E93'
  ];

  const getPartColor = (name) => {
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  if (!nestingData) {
    return (
      <div className={`flex items-center justify-center h-full text-[var(--text-secondary)] ${className}`}>
        <p>Generate CNC output to view nesting</p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
        
        {cncOutput && (
          <>
            <div className="neu-surface p-4 rounded-xl">
              <div className="flex items-center gap-2 text-[var(--text-secondary)] mb-1">
                <Clock size={16} />
                <span className="text-xs">Cut Time</span>
              </div>
              <p className="text-2xl font-bold font-mono">{Math.round(cncOutput.estimated_cut_time_minutes)}m</p>
            </div>
            
            <div className="neu-surface p-4 rounded-xl">
              <div className="flex items-center gap-2 text-[var(--text-secondary)] mb-1">
                <CurrencyDollar size={16} />
                <span className="text-xs">Material</span>
              </div>
              <p className="text-2xl font-bold font-mono">${cncOutput.material_cost_nzd}</p>
            </div>
          </>
        )}
      </div>

      {/* Sheet Visualizations */}
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
            
            {/* Sheet Visualization */}
            <div 
              className="relative bg-[#D4A574] rounded-lg overflow-hidden mx-auto"
              style={{
                width: SHEET_WIDTH * SCALE,
                height: SHEET_HEIGHT * SCALE,
              }}
            >
              {/* Wood grain pattern */}
              <div 
                className="absolute inset-0 opacity-30"
                style={{
                  backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(139,90,43,0.3) 2px, rgba(139,90,43,0.3) 4px)'
                }}
              />
              
              {/* Parts */}
              {sheet.parts.map((part, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: idx * 0.05 }}
                  className="absolute border-2 border-black/30 rounded-sm flex items-center justify-center overflow-hidden group cursor-pointer"
                  style={{
                    left: part.x * SCALE,
                    top: part.y * SCALE,
                    width: part.width * SCALE,
                    height: part.height * SCALE,
                    backgroundColor: getPartColor(part.name),
                  }}
                  title={`${part.name}: ${part.width}mm x ${part.height}mm${part.rotated ? ' (rotated)' : ''}`}
                >
                  {/* Part label - only show if big enough */}
                  {part.width * SCALE > 40 && part.height * SCALE > 25 && (
                    <span className="text-[8px] font-mono text-white text-center px-1 truncate">
                      {part.name}
                    </span>
                  )}
                  
                  {/* Hover tooltip */}
                  <div className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <div className="text-white text-center p-1">
                      <p className="text-[8px] font-bold truncate max-w-full">{part.name}</p>
                      <p className="text-[7px] font-mono">{part.width}x{part.height}</p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
            
            {/* Parts Legend */}
            <div className="mt-4 flex flex-wrap gap-2">
              {sheet.parts.map((part, idx) => (
                <div 
                  key={idx}
                  className="flex items-center gap-1 text-xs"
                >
                  <div 
                    className="w-3 h-3 rounded-sm"
                    style={{ backgroundColor: getPartColor(part.name) }}
                  />
                  <span className="font-mono text-[var(--text-secondary)]">
                    {part.name}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default NestingViewer;
