import React, { useRef, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowsOutSimple, Ruler, Cube } from '@phosphor-icons/react';

// Simple 2D desk visualization component 
const DeskPreview3D = ({ params, className = '' }) => {
  const [exploded, setExploded] = useState(false);
  const [showDimensions, setShowDimensions] = useState(false);
  const canvasRef = useRef(null);

  // Colors based on desk type
  const colors = {
    gaming: '#2A2A2A',
    studio: '#3D3D3D',
    office: '#D4A574'
  };
  
  const baseColor = colors[params.desk_type] || colors.office;
  const accentColor = params.has_rgb_channels ? '#FF3B30' : baseColor;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.fillStyle = '#1A1A1A';
    ctx.fillRect(0, 0, width, height);
    
    // Draw grid
    ctx.strokeStyle = '#333333';
    ctx.lineWidth = 0.5;
    for (let i = 0; i < width; i += 40) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, height);
      ctx.stroke();
    }
    for (let i = 0; i < height; i += 40) {
      ctx.beginPath();
      ctx.moveTo(0, i);
      ctx.lineTo(width, i);
      ctx.stroke();
    }
    
    // Scale factor
    const scale = Math.min(width / (params.width * 1.5), height / (params.height * 1.5));
    const centerX = width / 2;
    const centerY = height / 2;
    
    // Draw desk isometric view
    const deskW = params.width * scale * 0.5;
    const deskD = params.depth * scale * 0.3;
    const deskH = params.height * scale * 0.5;
    const t = params.material_thickness * scale * 0.1;
    
    const offsetX = exploded ? 20 : 0;
    const offsetY = exploded ? 15 : 0;
    
    // Draw shadow
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.beginPath();
    ctx.ellipse(centerX, centerY + deskH/2 + 30, deskW/2, deskD/3, 0, 0, Math.PI * 2);
    ctx.fill();
    
    // Draw legs (back)
    ctx.fillStyle = baseColor;
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    
    // Back left leg
    ctx.fillRect(centerX - deskW/2 + 10 - offsetX, centerY - deskH/2 + deskD/2 - offsetY, t * 3, deskH - 20);
    ctx.strokeRect(centerX - deskW/2 + 10 - offsetX, centerY - deskH/2 + deskD/2 - offsetY, t * 3, deskH - 20);
    
    // Back right leg
    ctx.fillRect(centerX + deskW/2 - 10 - t * 3 + offsetX, centerY - deskH/2 + deskD/2 - offsetY, t * 3, deskH - 20);
    ctx.strokeRect(centerX + deskW/2 - 10 - t * 3 + offsetX, centerY - deskH/2 + deskD/2 - offsetY, t * 3, deskH - 20);
    
    // Draw desktop top surface
    ctx.fillStyle = baseColor;
    ctx.beginPath();
    ctx.moveTo(centerX - deskW/2, centerY - deskH/2 + offsetY * 2);
    ctx.lineTo(centerX + deskW/2, centerY - deskH/2 + offsetY * 2);
    ctx.lineTo(centerX + deskW/2 + deskD/3, centerY - deskH/2 + deskD/2 + offsetY * 2);
    ctx.lineTo(centerX - deskW/2 + deskD/3, centerY - deskH/2 + deskD/2 + offsetY * 2);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    
    // Draw desktop front edge
    ctx.fillStyle = params.desk_type === 'gaming' ? '#1A1A1A' : '#8B6914';
    ctx.beginPath();
    ctx.moveTo(centerX - deskW/2, centerY - deskH/2 + offsetY * 2);
    ctx.lineTo(centerX + deskW/2, centerY - deskH/2 + offsetY * 2);
    ctx.lineTo(centerX + deskW/2, centerY - deskH/2 + t * 2 + offsetY * 2);
    ctx.lineTo(centerX - deskW/2, centerY - deskH/2 + t * 2 + offsetY * 2);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    
    // Draw RGB channel if enabled
    if (params.has_rgb_channels) {
      ctx.fillStyle = '#FF3B30';
      ctx.shadowColor = '#FF3B30';
      ctx.shadowBlur = 15;
      ctx.fillRect(centerX - deskW/2 + 20, centerY - deskH/2 + deskD/2 - 5 + offsetY * 2, deskW - 40, 4);
      ctx.shadowBlur = 0;
    }
    
    // Draw headset hook if enabled
    if (params.has_headset_hook) {
      ctx.fillStyle = accentColor;
      ctx.fillRect(centerX - deskW/2 - 15 - offsetX, centerY - deskH/2 - 10 + offsetY * 2, 12, 30);
      ctx.fillRect(centerX - deskW/2 - 15 - offsetX, centerY - deskH/2 + 20 + offsetY * 2, 20, 8);
    }
    
    // Draw mixer tray if enabled
    if (params.has_mixer_tray) {
      const mixerW = params.mixer_tray_width * scale * 0.3;
      ctx.fillStyle = baseColor;
      ctx.strokeStyle = '#000000';
      ctx.fillRect(centerX - mixerW/2, centerY - deskH/2 - 30 + offsetY * 3, mixerW, 25);
      ctx.strokeRect(centerX - mixerW/2, centerY - deskH/2 - 30 + offsetY * 3, mixerW, 25);
    }
    
    // Draw GPU tray if enabled
    if (params.has_gpu_tray) {
      ctx.fillStyle = '#1A1A1A';
      ctx.fillRect(centerX + deskW/4, centerY - deskH/2 + 15 + offsetY * 2, 60, 35);
      ctx.strokeRect(centerX + deskW/4, centerY - deskH/2 + 15 + offsetY * 2, 60, 35);
    }
    
    // Draw VESA mount if enabled
    if (params.has_vesa_mount) {
      ctx.fillStyle = '#1A1A1A';
      ctx.fillRect(centerX - 20, centerY - deskH/2 - 50 + offsetY * 4, 40, 40);
      ctx.strokeRect(centerX - 20, centerY - deskH/2 - 50 + offsetY * 4, 40, 40);
      // Monitor placeholder
      ctx.fillStyle = '#333333';
      ctx.fillRect(centerX - 80, centerY - deskH/2 - 120 + offsetY * 4, 160, 90);
      ctx.strokeRect(centerX - 80, centerY - deskH/2 - 120 + offsetY * 4, 160, 90);
    }
    
  }, [params, exploded, baseColor, accentColor]);

  return (
    <div className={`relative w-full h-full min-h-[400px] canvas-container ${className}`}>
      {/* Control buttons */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setExploded(!exploded)}
          className={`p-2 rounded-lg transition-smooth ${exploded ? 'bg-[var(--primary)] text-white' : 'neu-surface'}`}
          title="Explode View"
          data-testid="explode-view-btn"
        >
          <ArrowsOutSimple size={20} />
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowDimensions(!showDimensions)}
          className={`p-2 rounded-lg transition-smooth ${showDimensions ? 'bg-[var(--primary)] text-white' : 'neu-surface'}`}
          title="Show Dimensions"
          data-testid="show-dimensions-btn"
        >
          <Ruler size={20} />
        </motion.button>
      </div>

      {/* Stats overlay */}
      <div className="absolute bottom-4 left-4 z-10 glass-surface rounded-lg p-3">
        <div className="flex items-center gap-4 text-sm font-mono">
          <div>
            <span className="text-[var(--text-secondary)]">W:</span>
            <span className="ml-1">{params.width}mm</span>
          </div>
          <div>
            <span className="text-[var(--text-secondary)]">D:</span>
            <span className="ml-1">{params.depth}mm</span>
          </div>
          <div>
            <span className="text-[var(--text-secondary)]">H:</span>
            <span className="ml-1">{params.height}mm</span>
          </div>
        </div>
      </div>

      {/* Dimension labels */}
      {showDimensions && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-10">
          <div className="bg-black/80 text-white px-3 py-2 rounded text-sm font-mono whitespace-nowrap">
            {params.width}mm × {params.depth}mm × {params.height}mm
          </div>
        </div>
      )}

      {/* Type badge */}
      <div className="absolute top-4 left-4 z-10">
        <span className="px-3 py-1 rounded-full text-xs font-medium bg-[var(--primary)] text-white capitalize">
          {params.desk_type} Desk
        </span>
      </div>

      {/* 2D Canvas Preview */}
      <canvas 
        ref={canvasRef}
        width={800}
        height={500}
        className="w-full h-full object-contain"
        style={{ background: '#1A1A1A' }}
      />
      
      {/* 3D indicator */}
      <div className="absolute bottom-4 right-4 z-10 glass-surface rounded-lg p-2 flex items-center gap-2">
        <Cube size={16} className="text-[var(--primary)]" />
        <span className="text-xs text-[var(--text-secondary)]">2D Preview</span>
      </div>
    </div>
  );
};

export default DeskPreview3D;
