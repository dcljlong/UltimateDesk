import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Cube, Download, ArrowRight, Eye, FileCode, FilePdf, Info } from '@phosphor-icons/react';
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

export default function SharedQuote() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get(`${API}/pricing/shared/${slug}`)
      .then(({ data }) => setDoc(data))
      .catch(() => setError('Quote not found or link expired'));
  }, [slug]);

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
      </motion.div>
    </div>
  );
}
