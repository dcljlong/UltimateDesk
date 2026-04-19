import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Cube, Download, ArrowRight, Eye, FileCode, FilePdf, Info, Star } from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import axios from 'axios';

const getApiUrl = () => {
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return window.location.origin + '/api';
  }
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  return baseUrl + '/api';
};
const API = getApiUrl();

const fileIconFor = (k) => {
  if (k === 'dxf' || k === 'svg') return FileCode;
  if (k === 'pdf') return FilePdf;
  return Cube;
};

// Marketing-grade names mapped over backend presets (id must match preset id)
const CURATED_META = {
  office: {
    title: 'Minimal Office',
    tagline: 'Clean cable routing · VESA mount · 1600mm',
    accent: '#059669',
    bg: '#10231D',
  },
  gaming: {
    title: 'Gaming Pro',
    tagline: 'RGB channel · headset hook · 1800mm',
    accent: '#FF3B30',
    bg: '#2A1214',
  },
  studio: {
    title: 'Studio Beast',
    tagline: '610mm mixer tray · pedal tilt · 2000mm',
    accent: '#6366F1',
    bg: '#141726',
  },
};
const CURATED_ORDER = ['office', 'gaming', 'studio'];

// Tiny inline SVG desk illustration — scales with card color
const DeskGlyph = ({ color = '#FF3B30' }) => (
  <svg viewBox="0 0 120 70" className="w-full h-full" aria-hidden="true">
    <rect x="6" y="20" width="108" height="8" rx="1" fill={color} opacity="0.9" />
    <rect x="12" y="28" width="6" height="34" rx="1" fill={color} opacity="0.7" />
    <rect x="102" y="28" width="6" height="34" rx="1" fill={color} opacity="0.7" />
    <rect x="48" y="6" width="24" height="14" rx="1" fill="#ffffff" opacity="0.18" />
    <rect x="56" y="20" width="8" height="3" fill="#ffffff" opacity="0.25" />
    <line x1="0" y1="62" x2="120" y2="62" stroke={color} strokeOpacity="0.25" />
  </svg>
);

function PresetCard({ preset, quote, onBuild }) {
  const meta = CURATED_META[preset.id] || {
    title: preset.name,
    tagline: preset.description,
    accent: '#FF3B30',
    bg: '#1a1a1a',
  };
  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 260, damping: 22 }}
      className="neu-surface rounded-xl overflow-hidden flex flex-col"
      data-testid={`curated-card-${preset.id}`}
    >
      <div className="h-20 relative" style={{ background: meta.bg }}>
        <DeskGlyph color={meta.accent} />
      </div>
      <div className="p-4 flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] uppercase tracking-[0.18em] text-[var(--text-secondary)]">
            {preset.id}
          </span>
          {quote && (
            <span className="font-mono text-sm font-bold" data-testid={`curated-price-${preset.id}`}>
              from ${Math.round(quote.total)}
              <span className="ml-0.5 text-[10px] text-[var(--text-secondary)]">NZD</span>
            </span>
          )}
        </div>
        <h3 className="font-bold text-lg leading-tight" data-testid={`curated-title-${preset.id}`}>
          {meta.title}
        </h3>
        <p className="text-xs text-[var(--text-secondary)] mt-1 flex-1">{meta.tagline}</p>
        <Button
          variant="outline"
          className="w-full mt-3 justify-center"
          onClick={() => onBuild(preset.id)}
          data-testid={`curated-build-btn-${preset.id}`}
        >
          Build This <ArrowRight size={14} className="ml-1.5" />
        </Button>
      </div>
    </motion.div>
  );
}

export default function SharedQuote() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState(null);
  const [curated, setCurated] = useState([]);

  useEffect(() => {
    axios.get(`${API}/pricing/shared/${slug}`)
      .then(({ data }) => setDoc(data))
      .catch(() => setError('Quote not found or link expired'));
  }, [slug]);

  // Fetch the 3 curated presets + their live DXF prices in parallel
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data: presets } = await axios.get(`${API}/designs/presets`);
        const ordered = CURATED_ORDER
          .map((id) => presets.find((p) => p.id === id))
          .filter(Boolean);
        const quotes = await Promise.all(
          ordered.map((p) =>
            axios
              .post(`${API}/pricing/quote`, { params: p.params, bundle: 'dxf' })
              .then((r) => r.data)
              .catch(() => null)
          )
        );
        if (!cancelled) {
          setCurated(ordered.map((p, i) => ({ preset: p, quote: quotes[i] })));
        }
      } catch {
        /* panel hides on error */
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--background)] p-6">
        <div className="neu-surface p-8 rounded-xl text-center max-w-sm">
          <p className="text-[var(--text-secondary)] mb-4" data-testid="shared-quote-error">{error}</p>
          <Button onClick={() => navigate('/')}>Back to UltimateDesk</Button>
        </div>
      </div>
    );
  }
  if (!doc) {
    return <div className="min-h-screen flex items-center justify-center text-[var(--text-secondary)]">Loading quote…</div>;
  }

  const q = doc.quote;
  const p = doc.params;

  return (
    <div className="min-h-screen bg-[var(--background)] py-10 px-4">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl mx-auto"
        data-testid="shared-quote-root"
      >
        <header className="flex items-center gap-2 mb-8">
          <Cube size={28} weight="fill" className="text-[var(--primary)]" />
          <span className="font-bold">UltimateDesk CNC Pro</span>
          <span className="ml-auto flex items-center gap-1 text-xs text-[var(--text-secondary)]">
            <Eye size={12} /> {doc.views ?? 0} views
          </span>
        </header>

        <div className="neu-surface p-8 rounded-2xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-[0.2em] text-[var(--text-secondary)]">Quote</span>
            <span className="px-2.5 py-1 rounded-full bg-[var(--surface-elevated)] text-[10px] uppercase tracking-wider">
              {q.bundle_label}
            </span>
          </div>
          <h1 className="text-3xl font-black tracking-tight mb-1" data-testid="shared-quote-name">
            {doc.design_name}
          </h1>
          <p className="text-sm text-[var(--text-secondary)] mb-6" data-testid="shared-quote-headline">
            {q.headline}
          </p>

          <ul className="space-y-2.5 border-t border-[var(--border)] pt-4">
            {q.line_items.map((li, i) => (
              <li key={i} className="flex items-start justify-between gap-4 text-sm">
                <div>
                  <div>{li.label}</div>
                  {li.detail && <div className="text-xs text-[var(--text-secondary)]">{li.detail}</div>}
                </div>
                <span className="font-mono tabular-nums">${li.amount.toFixed(2)}</span>
              </li>
            ))}
            {q.commercial_license && (
              <li className="flex items-start justify-between gap-4 text-sm">
                <span>Commercial-use license</span>
                <span className="font-mono tabular-nums">${q.commercial_fee.toFixed(2)}</span>
              </li>
            )}
          </ul>

          <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 my-5 flex items-start gap-2 text-sm">
            <Info size={18} className="text-yellow-500 mt-0.5 flex-shrink-0" />
            <span data-testid="material-note">{q.material_note}</span>
          </div>

          <div className="flex items-baseline justify-between border-t-2 border-[var(--border)] pt-4">
            <span className="font-bold">Export total</span>
            <span className="text-4xl font-black text-[var(--primary)]" data-testid="shared-quote-total">
              ${Math.round(q.total)} <span className="text-base font-normal">NZD</span>
            </span>
          </div>

          <div className="flex flex-wrap gap-3 mt-6">
            <Button
              variant="outline"
              onClick={() => window.open(`${API}/pricing/shared/${slug}/pdf`, '_blank')}
              data-testid="shared-quote-pdf-btn"
            >
              <Download size={16} className="mr-2" /> Save as PDF
            </Button>
            <Button
              className="btn-primary"
              onClick={() => navigate('/designer')}
              data-testid="shared-quote-cta-btn"
            >
              Design your own <ArrowRight size={16} className="ml-2" />
            </Button>
          </div>

          <div className="mt-6 text-xs text-[var(--text-secondary)]">
            Bundle includes: {q.bundle_files.map((f) => {
              const I = fileIconFor(f);
              return <span key={f} className="inline-flex items-center gap-1 mr-3"><I size={12} /> {f.toUpperCase()}</span>;
            })}
          </div>
        </div>

        <p className="text-center text-xs text-[var(--text-secondary)] mt-6">
          Dimensions: {p.width}×{p.depth}×{p.height} mm · {q.sheets_required} sheet(s) · {q.part_count} parts
        </p>

        {/* ------ Other Popular Designs ------ */}
        {curated.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="mt-12"
            data-testid="curated-panel"
          >
            <div className="flex items-center gap-2 mb-1">
              <Star size={18} weight="fill" className="text-[var(--primary)]" />
              <h2 className="text-xl font-bold">Other Popular Designs</h2>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mb-5">
              No signup needed — just tap <strong>Build This</strong> and start designing.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {curated.map(({ preset, quote }) => (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  quote={quote}
                  onBuild={(id) => navigate(`/designer?preset=${id}`)}
                />
              ))}
            </div>
          </motion.section>
        )}
      </motion.div>
    </div>
  );
}
