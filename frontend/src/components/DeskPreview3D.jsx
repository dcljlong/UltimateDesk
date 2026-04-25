import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowsOutSimple,
  Cube,
  Headphones,
  Lamp,
  Lock,
  Monitor,
  MusicNote,
  Ruler,
} from '@phosphor-icons/react';
import { useAuth } from '../context/AuthContext';

const DeskPreview3D = ({ params, className = '' }) => {
  const { isPro, user } = useAuth();
  const isProtected = !isPro;
  const watermarkText = user?.email
    ? `UltimateDesk preview — ${user.email}`
    : 'UltimateDesk — preview only';

  const [exploded, setExploded] = useState(false);
  const [showDimensions, setShowDimensions] = useState(false);
  const [viewTransform, setViewTransform] = useState({ panX: 0, panY: 0, zoom: 1 });
  const dragStartRef = useRef(null);
  const canvasRef = useRef(null);

  const colorSchemes = {
    gaming: {
      top: '#1a1a1d',
      side: '#25252a',
      frame: '#101114',
      accent: '#ff4d43',
      accentSoft: '#ff8a80',
      panel: '#20232a',
    },
    studio: {
      top: '#2a2d34',
      side: '#353944',
      frame: '#171b22',
      accent: '#6366f1',
      accentSoft: '#a5b4fc',
      panel: '#242935',
    },
    office: {
      top: '#c69a6b',
      side: '#a98259',
      frame: '#3d4148',
      accent: '#059669',
      accentSoft: '#6ee7b7',
      panel: '#8f6b4a',
    },
  };

  const colors = colorSchemes[params.desk_type] || colorSchemes.office;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const widthPx = canvas.width;
    const heightPx = canvas.height;

    const deskWidth = Math.max(1000, params.width || 1800);
    const deskDepth = Math.max(600, params.depth || 700);
    const deskHeight = Math.max(680, params.height || 750);
    const t = Math.max(18, params.material_thickness || 18);

    const legSize = Math.max(44, Math.round(t * 2.4));
    const legInsetX = Math.max(70, Math.round(deskWidth * 0.08));
    const legInsetZ = Math.max(55, Math.round(deskDepth * 0.08));

    const clearSpanX = Math.max(300, deskWidth - ((legInsetX + legSize) * 2));
    const clearSpanZ = Math.max(220, deskDepth - ((legInsetZ + legSize) * 2));
    const backPanelW = Math.max(600, clearSpanX - 40);
    const backPanelH = params.desk_type === 'office' ? 180 : 220;
    const trayW = Math.max(500, Math.min(deskWidth - (legInsetX * 2) - 120, Math.round(deskWidth * 0.60)));

    const isOversize = Boolean(params.is_oversize) || deskWidth > 2400;
    const desktopSplitCount = isOversize ? Math.max(2, params.desktop_split_count || 2) : 1;
    const requiresCentreSupport = Boolean(params.requires_centre_support) || isOversize;

    const explodeLift = exploded ? 26 : 0;
    const explodeSpread = exploded ? 32 : 0;

    const baseUnit = Math.min(
      (widthPx * 0.56) / (deskWidth + deskDepth + 260),
      (heightPx * 0.66) / (deskHeight + deskDepth * 0.25 + 240)
    );
    const unit = baseUnit * viewTransform.zoom;

    const centerX = widthPx * 0.53 + viewTransform.panX;
    const floorY = heightPx * 0.84 + viewTransform.panY;
    const isoX = 0.58 * unit;
    const isoY = 0.22 * unit;

    const project = (x, y, z) => ({
      x: centerX + (x - z) * isoX,
      y: floorY - y * unit + (x + z) * isoY,
    });

    const shadeHex = (hex, amount) => {
      const clean = hex.replace('#', '');
      const num = Number.parseInt(clean, 16);
      const r = Math.max(0, Math.min(255, (num >> 16) + amount));
      const g = Math.max(0, Math.min(255, ((num >> 8) & 255) + amount));
      const b = Math.max(0, Math.min(255, (num & 255) + amount));
      return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
    };

    const rgba = (hex, alpha) => {
      const clean = hex.replace('#', '');
      const num = Number.parseInt(clean, 16);
      const r = num >> 16;
      const g = (num >> 8) & 255;
      const b = num & 255;
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    const pathFromPoints = (points) => {
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i += 1) {
        ctx.lineTo(points[i].x, points[i].y);
      }
      ctx.closePath();
    };

    const drawFace = (points, fill, stroke = 'rgba(0,0,0,0.22)') => {
      pathFromPoints(points);
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.stroke();
    };

    const drawCuboid = ({ x, y, z, w, h, d, topColor, rightColor, frontColor, edgeColor }) => {
      const p100 = project(x + w, y, z);
      const p110 = project(x + w, y, z + d);
      const p010 = project(x, y, z + d);
      const p001 = project(x, y + h, z);
      const p101 = project(x + w, y + h, z);
      const p111 = project(x + w, y + h, z + d);
      const p011 = project(x, y + h, z + d);

      drawFace([p010, p011, p111, p110], frontColor, edgeColor);
      drawFace([p100, p101, p111, p110], rightColor, edgeColor);
      drawFace([p001, p101, p111, p011], topColor, edgeColor);
    };

    const drawGlowLine = (start, end, color, thicknessPx = 4) => {
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = thicknessPx;
      ctx.shadowColor = color;
      ctx.shadowBlur = 18;
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
      ctx.restore();
    };

    const drawFloorShadow = () => {
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,0.18)';
      ctx.beginPath();
      ctx.ellipse(centerX, floorY + 20, deskWidth * unit * 0.33, deskDepth * unit * 0.11, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    };

    const frameTop = shadeHex(colors.frame, 14);
    const frameRight = shadeHex(colors.frame, -2);
    const frameFront = shadeHex(colors.frame, -14);

    const topGradient = ctx.createLinearGradient(0, 0, widthPx, heightPx);
    topGradient.addColorStop(0, shadeHex(colors.top, 14));
    topGradient.addColorStop(0.5, colors.top);
    topGradient.addColorStop(1, shadeHex(colors.top, -10));

    const panelTop = shadeHex(colors.panel, 10);
    const panelRight = shadeHex(colors.panel, -2);
    const panelFront = shadeHex(colors.panel, -12);

    ctx.clearRect(0, 0, widthPx, heightPx);

    const bg = ctx.createLinearGradient(0, 0, 0, heightPx);
    bg.addColorStop(0, '#f4f5f7');
    bg.addColorStop(1, '#eceff3');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, widthPx, heightPx);

    ctx.strokeStyle = 'rgba(80, 87, 101, 0.06)';
    ctx.lineWidth = 1;
    for (let x = 0; x < widthPx; x += 48) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, heightPx);
      ctx.stroke();
    }
    for (let y = 0; y < heightPx; y += 48) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(widthPx, y);
      ctx.stroke();
    }

    drawFloorShadow();

    // Rear posts
    drawCuboid({
      x: -deskWidth / 2 + legInsetX - explodeSpread,
      y: 0,
      z: deskDepth / 2 - legInsetZ - legSize + explodeSpread,
      w: legSize,
      h: deskHeight - t - explodeLift,
      d: legSize,
      topColor: frameTop,
      rightColor: frameRight,
      frontColor: frameFront,
      edgeColor: 'rgba(0,0,0,0.18)',
    });

    drawCuboid({
      x: deskWidth / 2 - legInsetX - legSize + explodeSpread,
      y: 0,
      z: deskDepth / 2 - legInsetZ - legSize + explodeSpread,
      w: legSize,
      h: deskHeight - t - explodeLift,
      d: legSize,
      topColor: frameTop,
      rightColor: frameRight,
      frontColor: frameFront,
      edgeColor: 'rgba(0,0,0,0.18)',
    });

    // Front posts
    drawCuboid({
      x: -deskWidth / 2 + legInsetX - explodeSpread,
      y: 0,
      z: -deskDepth / 2 + legInsetZ - explodeSpread,
      w: legSize,
      h: deskHeight - t - explodeLift,
      d: legSize,
      topColor: frameTop,
      rightColor: frameRight,
      frontColor: frameFront,
      edgeColor: 'rgba(0,0,0,0.18)',
    });

    drawCuboid({
      x: deskWidth / 2 - legInsetX - legSize + explodeSpread,
      y: 0,
      z: -deskDepth / 2 + legInsetZ - explodeSpread,
      w: legSize,
      h: deskHeight - t - explodeLift,
      d: legSize,
      topColor: frameTop,
      rightColor: frameRight,
      frontColor: frameFront,
      edgeColor: 'rgba(0,0,0,0.18)',
    });

    // Rear upper rail
    drawCuboid({
      x: -clearSpanX / 2,
      y: deskHeight * 0.60,
      z: deskDepth / 2 - legInsetZ - (legSize / 2) + explodeSpread,
      w: clearSpanX,
      h: 42,
      d: t,
      topColor: frameTop,
      rightColor: frameRight,
      frontColor: frameFront,
      edgeColor: 'rgba(0,0,0,0.18)',
    });

    // Front lower rail
    drawCuboid({
      x: -clearSpanX / 2,
      y: deskHeight * 0.16,
      z: -deskDepth / 2 + legInsetZ + (legSize / 2) - explodeSpread,
      w: clearSpanX,
      h: 30,
      d: t,
      topColor: frameTop,
      rightColor: frameRight,
      frontColor: frameFront,
      edgeColor: 'rgba(0,0,0,0.18)',
    });

    // Side rails
    drawCuboid({
      x: -deskWidth / 2 + legInsetX + (legSize - t) / 2 - explodeSpread,
      y: deskHeight * 0.16,
      z: -clearSpanZ / 2,
      w: t,
      h: 30,
      d: clearSpanZ,
      topColor: frameTop,
      rightColor: frameRight,
      frontColor: frameFront,
      edgeColor: 'rgba(0,0,0,0.18)',
    });

    drawCuboid({
      x: deskWidth / 2 - legInsetX - legSize + (legSize - t) / 2 + explodeSpread,
      y: deskHeight * 0.16,
      z: -clearSpanZ / 2,
      w: t,
      h: 30,
      d: clearSpanZ,
      topColor: frameTop,
      rightColor: frameRight,
      frontColor: frameFront,
      edgeColor: 'rgba(0,0,0,0.18)',
    });

    // Centre support for oversize split desks
    if (requiresCentreSupport) {
      const centreRailW = Math.max(420, Math.min(Math.round(deskWidth * 0.32), 900));

      drawCuboid({
        x: -legSize / 2,
        y: 0,
        z: -legSize / 2,
        w: legSize,
        h: deskHeight - t - explodeLift,
        d: legSize,
        topColor: frameTop,
        rightColor: frameRight,
        frontColor: frameFront,
        edgeColor: 'rgba(0,0,0,0.18)',
      });

      drawCuboid({
        x: -centreRailW / 2,
        y: deskHeight - 88,
        z: -t / 2,
        w: centreRailW,
        h: 55,
        d: t,
        topColor: frameTop,
        rightColor: frameRight,
        frontColor: frameFront,
        edgeColor: 'rgba(0,0,0,0.18)',
      });
    }

    // Back modesty panel
    drawCuboid({
      x: -backPanelW / 2,
      y: deskHeight * 0.32,
      z: deskDepth / 2 - legInsetZ - (legSize / 2) - t + explodeSpread,
      w: backPanelW,
      h: backPanelH,
      d: t,
      topColor: panelTop,
      rightColor: panelRight,
      frontColor: panelFront,
      edgeColor: 'rgba(0,0,0,0.20)',
    });

    // Cable tray
    if (params.has_cable_management) {
      const trayBaseY = deskHeight - 105;
      const trayZ = deskDepth * 0.06;
      drawCuboid({
        x: -trayW / 2,
        y: trayBaseY,
        z: trayZ,
        w: trayW,
        h: 12,
        d: 85,
        topColor: panelTop,
        rightColor: panelRight,
        frontColor: panelFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: -trayW / 2,
        y: trayBaseY + 12,
        z: trayZ,
        w: trayW,
        h: 50,
        d: t,
        topColor: panelTop,
        rightColor: panelRight,
        frontColor: panelFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: -trayW / 2,
        y: trayBaseY + 12,
        z: trayZ + 85 - t,
        w: trayW,
        h: 50,
        d: t,
        topColor: panelTop,
        rightColor: panelRight,
        frontColor: panelFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: -trayW / 2,
        y: trayBaseY + 12,
        z: trayZ,
        w: t,
        h: 50,
        d: 85,
        topColor: panelTop,
        rightColor: panelRight,
        frontColor: panelFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: trayW / 2 - t,
        y: trayBaseY + 12,
        z: trayZ,
        w: t,
        h: 50,
        d: 85,
        topColor: panelTop,
        rightColor: panelRight,
        frontColor: panelFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
    }

    // Mixer tray
    if (params.has_mixer_tray) {
      const mixerW = Math.max(280, Math.min(params.mixer_tray_width || 520, clearSpanX));
      drawCuboid({
        x: -mixerW / 2,
        y: deskHeight - 135,
        z: -deskDepth * 0.50,
        w: mixerW,
        h: t,
        d: 170,
        topColor: panelTop,
        rightColor: panelRight,
        frontColor: panelFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: -mixerW / 2,
        y: deskHeight - 135,
        z: -deskDepth * 0.50,
        w: 170,
        h: 120,
        d: t,
        topColor: frameTop,
        rightColor: frameRight,
        frontColor: frameFront,
        edgeColor: 'rgba(0,0,0,0.18)',
      });
      drawCuboid({
        x: mixerW / 2 - 170,
        y: deskHeight - 135,
        z: -deskDepth * 0.50,
        w: 170,
        h: 120,
        d: t,
        topColor: frameTop,
        rightColor: frameRight,
        frontColor: frameFront,
        edgeColor: 'rgba(0,0,0,0.18)',
      });
    }

    // Headset hook
    if (params.has_headset_hook) {
      drawCuboid({
        x: -deskWidth / 2 - 14,
        y: deskHeight - 120,
        z: -deskDepth * 0.12,
        w: 14,
        h: 90,
        d: 12,
        topColor: colors.accent,
        rightColor: shadeHex(colors.accent, -14),
        frontColor: shadeHex(colors.accent, -24),
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: -deskWidth / 2 - 14,
        y: deskHeight - 42,
        z: -deskDepth * 0.12,
        w: 46,
        h: 12,
        d: 12,
        topColor: colors.accentSoft,
        rightColor: colors.accent,
        frontColor: shadeHex(colors.accent, -16),
        edgeColor: 'rgba(0,0,0,0.20)',
      });
    }

    // GPU tray
    if (params.has_gpu_tray) {
      drawCuboid({
        x: deskWidth * 0.12,
        y: deskHeight - 180,
        z: deskDepth * 0.04,
        w: 150,
        h: 12,
        d: 70,
        topColor: panelTop,
        rightColor: panelRight,
        frontColor: panelFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: deskWidth * 0.12,
        y: deskHeight - 168,
        z: deskDepth * 0.04,
        w: 70,
        h: 70,
        d: t,
        topColor: frameTop,
        rightColor: frameRight,
        frontColor: frameFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: deskWidth * 0.12 + 150 - 70,
        y: deskHeight - 168,
        z: deskDepth * 0.04,
        w: 70,
        h: 70,
        d: t,
        topColor: frameTop,
        rightColor: frameRight,
        frontColor: frameFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
    }

    // Monitor/VESA
    if (params.has_vesa_mount) {
      drawCuboid({
        x: -16,
        y: deskHeight + t,
        z: -deskDepth * 0.18,
        w: 32,
        h: 180,
        d: 16,
        topColor: frameTop,
        rightColor: frameRight,
        frontColor: frameFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: -100,
        y: deskHeight + t + 60,
        z: -deskDepth * 0.18,
        w: 120,
        h: 120,
        d: 12,
        topColor: panelTop,
        rightColor: panelRight,
        frontColor: panelFront,
        edgeColor: 'rgba(0,0,0,0.20)',
      });
      drawCuboid({
        x: 20,
        y: deskHeight + t + 20,
        z: -deskDepth * 0.18,
        w: 200,
        h: 200,
        d: 16,
        topColor: '#1f2732',
        rightColor: '#171d26',
        frontColor: '#1b212a',
        edgeColor: 'rgba(0,0,0,0.20)',
      });
    }

    // Desktop top
    if (desktopSplitCount > 1) {
      const leftTopW = Math.ceil(deskWidth / 2);
      const rightTopW = deskWidth - leftTopW;

      drawCuboid({
        x: -deskWidth / 2,
        y: deskHeight - explodeLift,
        z: -deskDepth / 2,
        w: leftTopW,
        h: t,
        d: deskDepth,
        topColor: topGradient,
        rightColor: shadeHex(colors.side, -4),
        frontColor: shadeHex(colors.side, -16),
        edgeColor: 'rgba(0,0,0,0.20)',
      });

      drawCuboid({
        x: -deskWidth / 2 + leftTopW,
        y: deskHeight - explodeLift,
        z: -deskDepth / 2,
        w: rightTopW,
        h: t,
        d: deskDepth,
        topColor: topGradient,
        rightColor: shadeHex(colors.side, -4),
        frontColor: shadeHex(colors.side, -16),
        edgeColor: 'rgba(0,0,0,0.20)',
      });

      drawCuboid({
        x: -4,
        y: deskHeight - explodeLift + 2,
        z: -deskDepth / 2,
        w: 8,
        h: t + 4,
        d: deskDepth,
        topColor: colors.accentSoft,
        rightColor: colors.accent,
        frontColor: shadeHex(colors.accent, -16),
        edgeColor: 'rgba(0,0,0,0.24)',
      });
    } else {
      drawCuboid({
        x: -deskWidth / 2,
        y: deskHeight - explodeLift,
        z: -deskDepth / 2,
        w: deskWidth,
        h: t,
        d: deskDepth,
        topColor: topGradient,
        rightColor: shadeHex(colors.side, -4),
        frontColor: shadeHex(colors.side, -16),
        edgeColor: 'rgba(0,0,0,0.20)',
      });
    }

    if (isProtected) {
      ctx.save();
      ctx.globalAlpha = 0.12;
      ctx.fillStyle = '#2f3742';
      ctx.font = 'bold 18px Helvetica, Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.translate(widthPx / 2, heightPx / 2);
      ctx.rotate(-Math.PI / 7);
      for (let yy = -heightPx; yy < heightPx; yy += 120) {
        for (let xx = -widthPx; xx < widthPx; xx += 320) {
          ctx.fillText(watermarkText, xx, yy);
        }
      }
      ctx.restore();
    }
  }, [colors, exploded, isProtected, params, viewTransform, watermarkText]);

  const roundToRange = (value, step = 50) => `~${Math.round(value / step) * step}`;
  const fmtDim = (value) => (isProtected ? roundToRange(value) : `${value}`);
  const fmtMat = (value) => (isProtected ? '18' : `${value}`);

  const activeFeatures = [];
  if (params.has_cable_management) activeFeatures.push({ icon: Cube, label: 'Cable tray' });
  if (params.has_mixer_tray) activeFeatures.push({ icon: MusicNote, label: 'Mixer tray' });
  if (params.has_headset_hook) activeFeatures.push({ icon: Headphones, label: 'Hook' });
  if (params.has_gpu_tray) activeFeatures.push({ icon: Cube, label: 'GPU tray' });
  if (params.has_vesa_mount) activeFeatures.push({ icon: Monitor, label: 'VESA' });
  if (params.is_oversize || params.width > 2400) activeFeatures.push({ icon: Cube, label: 'Split top' });
  if (params.requires_centre_support || params.is_oversize || params.width > 2400) activeFeatures.push({ icon: Cube, label: 'Centre support' });

  const handlePointerDown = (event) => {
    dragStartRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      panX: viewTransform.panX,
      panY: viewTransform.panY,
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const handlePointerMove = (event) => {
    if (!dragStartRef.current) return;

    const start = dragStartRef.current;
    setViewTransform((prev) => ({
      ...prev,
      panX: start.panX + (event.clientX - start.startX),
      panY: start.panY + (event.clientY - start.startY),
    }));
  };

  const stopDragging = (event) => {
    if (dragStartRef.current?.pointerId === event.pointerId) {
      event.currentTarget.releasePointerCapture?.(event.pointerId);
    }
    dragStartRef.current = null;
  };

  const handleWheel = (event) => {
    event.preventDefault();

    const zoomDelta = event.deltaY > 0 ? -0.08 : 0.08;
    setViewTransform((prev) => ({
      ...prev,
      zoom: Math.min(1.8, Math.max(0.65, Number((prev.zoom + zoomDelta).toFixed(2)))),
    }));
  };

  return (
    <div
      className={`relative w-full h-full min-h-[400px] ${className}`}
      onContextMenu={isProtected ? (e) => e.preventDefault() : undefined}
      onDragStart={isProtected ? (e) => e.preventDefault() : undefined}
      style={isProtected ? { userSelect: 'none', WebkitUserSelect: 'none' } : undefined}
      data-testid="desk-preview-root"
    >
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

      <div className="absolute top-4 left-4 z-10 flex gap-2">
        <span className="px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-[var(--primary)] text-white shadow-lg">
          {params.desk_type} Desk
        </span>
        <span className="px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-white/85 text-slate-700 shadow-sm">
          Straight frame
        </span>
        {(params.is_oversize || params.width > 2400) && (
          <span className="px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-500 text-white shadow-lg">
            Oversize split top
          </span>
        )}
      </div>

      {activeFeatures.length > 0 && (
        <div className="absolute top-14 left-4 z-10 flex flex-col gap-2">
          {activeFeatures.map((feature, idx) => (
            <motion.div
              key={feature.label}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="flex items-center gap-2 px-2 py-1 rounded-md bg-white/80 backdrop-blur-sm text-xs shadow-sm"
            >
              <feature.icon size={14} className="text-[var(--primary)]" />
              <span>{feature.label}</span>
            </motion.div>
          ))}
        </div>
      )}

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
            {(params.is_oversize || params.width > 2400) && (
              <>
                <div className="flex justify-between gap-4 pt-1 border-t border-[var(--border)]">
                  <span className="text-[var(--text-secondary)]">Split top:</span>
                  <span className="font-bold">{params.desktop_split_count || 2} panels</span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-[var(--text-secondary)]">Centre support:</span>
                  <span className="font-bold">Required</span>
                </div>
              </>
            )}
          </div>
        </motion.div>
      )}

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

      <div className="absolute bottom-4 right-4 z-10 glass-surface rounded-lg px-3 py-2 flex items-center gap-2">
        <Cube size={16} className="text-[var(--primary)]" />
        <span className="text-xs font-medium">Drag / scroll to inspect</span>
      </div>

      <canvas
        ref={canvasRef}
        width={900}
        height={600}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={stopDragging}
        onPointerLeave={stopDragging}
        onWheel={handleWheel}
        onDoubleClick={() => setViewTransform({ panX: 0, panY: 0, zoom: 1 })}
        title="Drag to move, mouse wheel to zoom, double-click to reset"
        style={{ touchAction: 'none' }}
        className="w-full h-full object-contain rounded-lg cursor-grab active:cursor-grabbing"
      />
    </div>
  );
};

export default DeskPreview3D;
