import React, { useRef, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowsOutSimple, Ruler, Cube, Monitor, Headphones, Lamp, MusicNote, Lock } from '@phosphor-icons/react';
import { useAuth } from '../context/AuthContext';

const DeskPreview3D = ({ params, className = '' }) => {
  const { isPro, user } = useAuth();
  const isProtected = !isPro;
  const watermarkText = user?.email
    ? `UltimateDesk preview — ${user.email}`
    : 'UltimateDesk — preview only';
  const [exploded, setExploded] = useState(false);
  const [showDimensions, setShowDimensions] = useState(false);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const rotationRef = useRef(0);

  // Colors based on desk type
  const colorSchemes = {
    gaming: { 
      primary: '#1A1A1A', 
      secondary: '#2A2A2A', 
      accent: '#FF3B30',
      highlight: '#FF6B5B'
    },
    studio: { 
      primary: '#2D2D2D', 
      secondary: '#3D3D3D', 
      accent: '#6366F1',
      highlight: '#818CF8'
    },
    office: { 
      primary: '#D4A574', 
      secondary: '#B8956E', 
      accent: '#059669',
      highlight: '#34D399'
    }
  };
  
  const colors = colorSchemes[params.desk_type] || colorSchemes.office;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    const draw = () => {
      // Clear canvas with gradient background
      const bgGradient = ctx.createRadialGradient(width/2, height/2, 0, width/2, height/2, width);
      bgGradient.addColorStop(0, '#1F1F1F');
      bgGradient.addColorStop(1, '#0D0D0D');
      ctx.fillStyle = bgGradient;
      ctx.fillRect(0, 0, width, height);
      
      // Draw grid with perspective feel
      ctx.strokeStyle = 'rgba(255,255,255,0.03)';
      ctx.lineWidth = 1;
      for (let i = 0; i < width; i += 50) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, height);
        ctx.stroke();
      }
      for (let i = 0; i < height; i += 50) {
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(width, i);
        ctx.stroke();
      }
      
      // Scale factor
      const scale = Math.min(width / (params.width * 1.3), height / (params.height * 2)) * 0.8;
      const centerX = width / 2;
      const centerY = height / 2 + 50;
      
      // Isometric projection settings
      const isoAngle = Math.PI / 6;
      const deskW = params.width * scale * 0.55;
      const deskD = params.depth * scale * 0.35;
      const deskH = params.height * scale * 0.55;
      const t = Math.max(params.material_thickness * scale * 0.15, 4);
      
      const offsetX = exploded ? 25 : 0;
      const offsetY = exploded ? 20 : 0;
      
      // Subtle rotation animation
      const wobble = Math.sin(rotationRef.current * 0.02) * 3;
      
      // Helper function for isometric transformation
      const isoX = (x, z) => centerX + (x - z) * Math.cos(isoAngle) + wobble;
      const isoY = (y, x, z) => centerY - y + (x + z) * Math.sin(isoAngle) * 0.5;
      
      // Draw floor shadow
      ctx.fillStyle = 'rgba(0,0,0,0.4)';
      ctx.beginPath();
      ctx.ellipse(centerX + wobble, centerY + deskH * 0.5 + 60, deskW * 0.7, deskD * 0.5, 0, 0, Math.PI * 2);
      ctx.fill();
      
      // Draw back legs first (behind desk)
      ctx.fillStyle = colors.secondary;
      ctx.strokeStyle = 'rgba(0,0,0,0.5)';
      ctx.lineWidth = 1;
      
      // Back left leg
      const legWidth = t * 3;
      const legDepth = deskD * 0.9;
      
      drawIsometricBox(ctx, 
        isoX(-deskW/2 + legWidth/2 - offsetX, -legDepth/2 - offsetY),
        isoY(deskH * 0.85, -deskW/2 + legWidth/2, -legDepth/2),
        legWidth, deskH * 0.85, legDepth * 0.15,
        colors.primary, colors.secondary
      );
      
      // Back right leg
      drawIsometricBox(ctx,
        isoX(deskW/2 - legWidth/2 + offsetX, -legDepth/2 - offsetY),
        isoY(deskH * 0.85, deskW/2 - legWidth/2, -legDepth/2),
        legWidth, deskH * 0.85, legDepth * 0.15,
        colors.primary, colors.secondary
      );
      
      // Draw back panel/stretcher
      drawIsometricBox(ctx,
        isoX(0, -legDepth/2 - offsetY * 1.5),
        isoY(deskH * 0.6, 0, -legDepth/2),
        deskW - legWidth * 3, deskH * 0.25, t,
        colors.primary, colors.secondary
      );
      
      // Cable management tray
      if (params.has_cable_management) {
        ctx.fillStyle = '#111111';
        drawIsometricBox(ctx,
          isoX(0, -legDepth/2 + t),
          isoY(deskH * 0.75 - offsetY * 2, 0, -legDepth/2),
          deskW - legWidth * 4, t, legDepth * 0.2,
          '#1A1A1A', '#111111'
        );
      }
      
      // Draw desktop (main surface)
      const desktopGradient = ctx.createLinearGradient(
        centerX - deskW/2, centerY - deskH,
        centerX + deskW/2, centerY - deskH + deskD
      );
      desktopGradient.addColorStop(0, colors.primary);
      desktopGradient.addColorStop(0.5, colors.secondary);
      desktopGradient.addColorStop(1, colors.primary);
      
      drawIsometricBox(ctx,
        isoX(0, 0),
        isoY(deskH + offsetY * 2, 0, 0),
        deskW, t * 2, deskD,
        colors.primary, colors.secondary, desktopGradient
      );
      
      // Front legs
      drawIsometricBox(ctx,
        isoX(-deskW/2 + legWidth/2 - offsetX, legDepth/2 + offsetY),
        isoY(deskH * 0.85, -deskW/2 + legWidth/2, legDepth/2),
        legWidth, deskH * 0.85, legDepth * 0.15,
        colors.primary, colors.secondary
      );
      
      drawIsometricBox(ctx,
        isoX(deskW/2 - legWidth/2 + offsetX, legDepth/2 + offsetY),
        isoY(deskH * 0.85, deskW/2 - legWidth/2, legDepth/2),
        legWidth, deskH * 0.85, legDepth * 0.15,
        colors.primary, colors.secondary
      );
      
      // Front stretcher
      drawIsometricBox(ctx,
        isoX(0, legDepth/2 + offsetY * 1.5),
        isoY(t * 3, 0, legDepth/2),
        deskW - legWidth * 3, t * 2, t,
        colors.primary, colors.secondary
      );
      
      // RGB Channel (glow effect)
      if (params.has_rgb_channels) {
        ctx.shadowColor = colors.accent;
        ctx.shadowBlur = 20;
        ctx.fillStyle = colors.accent;
        ctx.beginPath();
        ctx.moveTo(isoX(-deskW/2 + 30, -legDepth/2), isoY(deskH + offsetY * 2 - t, -deskW/2 + 30, -legDepth/2));
        ctx.lineTo(isoX(deskW/2 - 30, -legDepth/2), isoY(deskH + offsetY * 2 - t, deskW/2 - 30, -legDepth/2));
        ctx.lineTo(isoX(deskW/2 - 30, -legDepth/2), isoY(deskH + offsetY * 2 - t + 4, deskW/2 - 30, -legDepth/2));
        ctx.lineTo(isoX(-deskW/2 + 30, -legDepth/2), isoY(deskH + offsetY * 2 - t + 4, -deskW/2 + 30, -legDepth/2));
        ctx.fill();
        ctx.shadowBlur = 0;
      }
      
      // Headset hook
      if (params.has_headset_hook) {
        const hookX = -deskW/2 - 15 - offsetX;
        ctx.fillStyle = colors.accent;
        ctx.shadowColor = colors.accent;
        ctx.shadowBlur = 10;
        drawIsometricBox(ctx,
          isoX(hookX, 0),
          isoY(deskH + offsetY * 3, hookX, 0),
          12, 40, 8,
          colors.accent, colors.highlight
        );
        drawIsometricBox(ctx,
          isoX(hookX + 8, 0),
          isoY(deskH + offsetY * 3 - 35, hookX + 8, 0),
          20, 8, 8,
          colors.accent, colors.highlight
        );
        ctx.shadowBlur = 0;
      }
      
      // Mixer tray
      if (params.has_mixer_tray) {
        const mixerW = params.mixer_tray_width * scale * 0.4;
        drawIsometricBox(ctx,
          isoX(0, -legDepth/2 - 20 - offsetY * 3),
          isoY(deskH + offsetY * 2 + 30, 0, -legDepth/2 - 20),
          mixerW, t * 1.5, legDepth * 0.4,
          colors.primary, colors.secondary
        );
        // Angled supports
        ctx.fillStyle = colors.secondary;
        ctx.beginPath();
        ctx.moveTo(isoX(-mixerW/3, -legDepth/2), isoY(deskH + offsetY * 2, -mixerW/3, -legDepth/2));
        ctx.lineTo(isoX(-mixerW/3, -legDepth/2 - 20), isoY(deskH + offsetY * 2 + 30, -mixerW/3, -legDepth/2 - 20));
        ctx.lineTo(isoX(-mixerW/3 + 8, -legDepth/2 - 20), isoY(deskH + offsetY * 2 + 30, -mixerW/3 + 8, -legDepth/2 - 20));
        ctx.fill();
      }
      
      // GPU Tray
      if (params.has_gpu_tray) {
        drawIsometricBox(ctx,
          isoX(deskW/4, legDepth/4 + offsetY),
          isoY(deskH + offsetY * 2 - t * 3, deskW/4, legDepth/4),
          60, t, 35,
          '#1A1A1A', '#111111'
        );
      }
      
      // VESA Mount
      if (params.has_vesa_mount) {
        ctx.fillStyle = '#1A1A1A';
        drawIsometricBox(ctx,
          isoX(0, -legDepth/3 - offsetY * 5),
          isoY(deskH + offsetY * 4 + 80, 0, -legDepth/3),
          30, 80, 8,
          '#1A1A1A', '#111111'
        );
        // Monitor placeholder
        ctx.fillStyle = '#222222';
        drawIsometricBox(ctx,
          isoX(0, -legDepth/3 - offsetY * 5),
          isoY(deskH + offsetY * 4 + 180, 0, -legDepth/3),
          200, 120, 10,
          '#2A2A2A', '#1A1A1A'
        );
        // Screen
        ctx.fillStyle = '#3B3B3B';
        const screenGlow = ctx.createLinearGradient(
          centerX - 80, centerY - deskH - 100,
          centerX + 80, centerY - deskH
        );
        screenGlow.addColorStop(0, '#4A4A4A');
        screenGlow.addColorStop(0.5, '#3A3A3A');
        screenGlow.addColorStop(1, '#2A2A2A');
        ctx.fillStyle = screenGlow;
        ctx.beginPath();
        ctx.moveTo(isoX(-85, -legDepth/3 - offsetY * 5), isoY(deskH + offsetY * 4 + 175, -85, -legDepth/3));
        ctx.lineTo(isoX(85, -legDepth/3 - offsetY * 5), isoY(deskH + offsetY * 4 + 175, 85, -legDepth/3));
        ctx.lineTo(isoX(85, -legDepth/3 - offsetY * 5), isoY(deskH + offsetY * 4 + 70, 85, -legDepth/3));
        ctx.lineTo(isoX(-85, -legDepth/3 - offsetY * 5), isoY(deskH + offsetY * 4 + 70, -85, -legDepth/3));
        ctx.fill();
      }
      
      // Increment rotation for animation
      rotationRef.current += 1;

      // === COPY PROTECTION: diagonal watermark for non-Pro ===
      if (isProtected) {
        ctx.save();
        ctx.globalAlpha = 0.22;
        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 20px Helvetica, Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.translate(width / 2, height / 2);
        ctx.rotate(-Math.PI / 7);
        const stepY = 130;
        for (let yy = -height; yy < height; yy += stepY) {
          for (let xx = -width; xx < width; xx += 380) {
            ctx.fillText(watermarkText, xx, yy);
          }
        }
        ctx.restore();

        // Subtle noise layer to discourage clean screenshot vectorisation
        ctx.save();
        ctx.globalAlpha = 0.05;
        for (let i = 0; i < 800; i++) {
          ctx.fillStyle = Math.random() > 0.5 ? '#FFFFFF' : '#000000';
          ctx.fillRect(Math.random() * width, Math.random() * height, 1, 1);
        }
        ctx.restore();
      }

      animationRef.current = requestAnimationFrame(draw);
    };
    
    draw();
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [params, exploded, colors, isProtected, watermarkText]);

  // Helper function to draw isometric box
  function drawIsometricBox(ctx, x, y, w, h, d, colorTop, colorSide, customTop = null) {
    const isoAngle = Math.PI / 6;
    const cosA = Math.cos(isoAngle);
    const sinA = Math.sin(isoAngle);
    
    // Top face
    ctx.fillStyle = customTop || colorTop;
    ctx.beginPath();
    ctx.moveTo(x, y - h);
    ctx.lineTo(x + w/2 * cosA, y - h - w/2 * sinA);
    ctx.lineTo(x + w/2 * cosA - d/2 * cosA, y - h - w/2 * sinA - d/2 * sinA);
    ctx.lineTo(x - d/2 * cosA, y - h - d/2 * sinA);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = 'rgba(0,0,0,0.3)';
    ctx.stroke();
    
    // Right face
    ctx.fillStyle = colorSide;
    ctx.beginPath();
    ctx.moveTo(x + w/2 * cosA, y - h - w/2 * sinA);
    ctx.lineTo(x + w/2 * cosA, y - w/2 * sinA);
    ctx.lineTo(x + w/2 * cosA - d/2 * cosA, y - w/2 * sinA - d/2 * sinA);
    ctx.lineTo(x + w/2 * cosA - d/2 * cosA, y - h - w/2 * sinA - d/2 * sinA);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    
    // Left face  
    const darkerSide = adjustBrightness(colorSide, -30);
    ctx.fillStyle = darkerSide;
    ctx.beginPath();
    ctx.moveTo(x, y - h);
    ctx.lineTo(x, y);
    ctx.lineTo(x - d/2 * cosA, y - d/2 * sinA);
    ctx.lineTo(x - d/2 * cosA, y - h - d/2 * sinA);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  function adjustBrightness(hex, amount) {
    const num = parseInt(hex.replace('#', ''), 16);
    const r = Math.min(255, Math.max(0, (num >> 16) + amount));
    const g = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amount));
    const b = Math.min(255, Math.max(0, (num & 0x0000FF) + amount));
    return '#' + (b | (g << 8) | (r << 16)).toString(16).padStart(6, '0');
  }

  // Dimension display helpers (copy protection: round/obscure for non-Pro)
  const roundToRange = (v, step = 50) => `~${Math.round(v / step) * step}`;
  const fmtDim = (v) => (isProtected ? roundToRange(v) : `${v}`);
  const fmtMat = (v) => (isProtected ? '18' : `${v}`);

  // Feature icons
  const activeFeatures = [];
  if (params.has_rgb_channels) activeFeatures.push({ icon: Lamp, label: 'RGB' });
  if (params.has_headset_hook) activeFeatures.push({ icon: Headphones, label: 'Hook' });
  if (params.has_vesa_mount) activeFeatures.push({ icon: Monitor, label: 'VESA' });
  if (params.has_mixer_tray) activeFeatures.push({ icon: MusicNote, label: 'Mixer' });

  return (
    <div
      className={`relative w-full h-full min-h-[400px] ${className}`}
      onContextMenu={isProtected ? (e) => e.preventDefault() : undefined}
      onDragStart={isProtected ? (e) => e.preventDefault() : undefined}
      style={isProtected ? { userSelect: 'none', WebkitUserSelect: 'none' } : undefined}
      data-testid="desk-preview-root"
    >
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

      {/* Type badge */}
      <div className="absolute top-4 left-4 z-10">
        <span className="px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-[var(--primary)] text-white shadow-lg">
          {params.desk_type} Desk
        </span>
      </div>

      {/* Active features */}
      {activeFeatures.length > 0 && (
        <div className="absolute top-14 left-4 z-10 flex flex-col gap-2">
          {activeFeatures.map((feature, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="flex items-center gap-2 px-2 py-1 rounded-md bg-[var(--surface)]/80 backdrop-blur-sm text-xs"
            >
              <feature.icon size={14} className="text-[var(--primary)]" />
              <span>{feature.label}</span>
            </motion.div>
          ))}
        </div>
      )}

      {/* Dimension labels */}
      {showDimensions && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute top-16 right-4 z-10 neu-surface rounded-lg p-3"
          data-testid="dimension-panel"
        >
          <div className="space-y-1 text-sm font-mono">
            <div className="flex justify-between gap-4">
              <span className="text-[var(--text-secondary)]">Width:</span>
              <span className="font-bold">{fmtDim(params.width)}mm</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-[var(--text-secondary)]">Depth:</span>
              <span className="font-bold">{fmtDim(params.depth)}mm</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-[var(--text-secondary)]">Height:</span>
              <span className="font-bold">{fmtDim(params.height)}mm</span>
            </div>
            <div className="flex justify-between gap-4 pt-1 border-t border-[var(--border)]">
              <span className="text-[var(--text-secondary)]">Material:</span>
              <span className="font-bold">{fmtMat(params.material_thickness)}mm</span>
            </div>
            {isProtected && (
              <div className="pt-2 mt-1 border-t border-[var(--border)] flex items-center gap-1.5 text-[10px] text-[var(--text-secondary)]">
                <Lock size={11} /> Exact values unlocked after export
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Stats overlay */}
      <div className="absolute bottom-4 left-4 z-10 glass-surface rounded-lg p-3" data-testid="preview-stats">
        <div className="flex items-center gap-4 text-sm font-mono">
          <div>
            <span className="text-[var(--text-secondary)]">W:</span>
            <span className="ml-1 font-bold">{fmtDim(params.width)}</span>
          </div>
          <div>
            <span className="text-[var(--text-secondary)]">D:</span>
            <span className="ml-1 font-bold">{fmtDim(params.depth)}</span>
          </div>
          <div>
            <span className="text-[var(--text-secondary)]">H:</span>
            <span className="ml-1 font-bold">{fmtDim(params.height)}</span>
          </div>
          {isProtected && (
            <span className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-[var(--text-secondary)] border-l border-[var(--border)] pl-3">
              <Lock size={10} /> preview
            </span>
          )}
        </div>
      </div>
      
      {/* 3D indicator */}
      <div className="absolute bottom-4 right-4 z-10 glass-surface rounded-lg px-3 py-2 flex items-center gap-2">
        <Cube size={16} className="text-[var(--primary)]" />
        <span className="text-xs font-medium">Isometric View</span>
      </div>

      {/* Canvas */}
      <canvas 
        ref={canvasRef}
        width={900}
        height={600}
        className="w-full h-full object-contain rounded-lg"
      />
    </div>
  );
};

export default DeskPreview3D;

