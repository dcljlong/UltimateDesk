import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Download,
  Crown,
  FileCode,
  Cube,
  FilePdf,
  Warning,
  Spinner,
  ArrowRight,
  Lock,
  CheckCircle,
  Info,
  Share,
  Check,
  Copy,
} from '@phosphor-icons/react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const getApiUrl = () => {
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  if (baseUrl) {
    return baseUrl + '/api';
  }
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return window.location.origin + '/api';
  }
  return '/api';
};
const FILE_META = {
  dxf:   { Icon: FileCode, label: 'DXF',    color: 'text-blue-500',  hint: 'CAD/CAM geometry' },
  svg:   { Icon: FileCode, label: 'SVG',    color: 'text-purple-500',hint: 'Vector cut layout' },
  gcode: { Icon: Cube,     label: 'NC',     color: 'text-green-500', hint: 'Machine file' },
  pdf:   { Icon: FilePdf,  label: 'PDF',    color: 'text-red-500',   hint: 'Cut-sheet reference' },
};

const ExportDialog = ({ isOpen, onClose, params, designName }) => {
  const { isAuthenticated, isPro } = useAuth();
  const navigate = useNavigate();

  const [bundle, setBundle] = useState('dxf');
  const [commercial, setCommercial] = useState(false);
  const [catalog, setCatalog] = useState(null);
  const [quote, setQuote] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);

  const [accessStatus, setAccessStatus] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [exportResult, setExportResult] = useState(null);
  const [error, setError] = useState(null);
  const [shareLink, setShareLink] = useState(null);
  const [isSharing, setIsSharing] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);

  // Load bundle catalog once
  useEffect(() => {
    if (!isOpen) return;
    axios.get(`${API}/pricing/bundles`).then(({ data }) => setCatalog(data)).catch(() => {});
  }, [isOpen]);

  // Check export access when dialog opens
  useEffect(() => {
    if (isOpen && isAuthenticated) {
      checkAccess();
    }
  }, [isOpen, isAuthenticated]);

  // Live quote - debounced on params / bundle / commercial change
  useEffect(() => {
    if (!isOpen) return;
    const handle = setTimeout(async () => {
      setQuoteLoading(true);
      try {
        const { data } = await axios.post(`${API}/pricing/quote`, {
          params,
          bundle,
          commercial_license: commercial,
        });
        setQuote(data);
      } catch (e) {
        console.error('Quote error:', e);
      } finally {
        setQuoteLoading(false);
      }
    }, 200);
    return () => clearTimeout(handle);
  }, [isOpen, params, bundle, commercial]);

  const checkAccess = async () => {
    setIsChecking(true);
    try {
      const { data } = await axios.post(`${API}/exports/check-access`, {}, { withCredentials: true });
      setAccessStatus(data);
    } catch {
      setAccessStatus({ has_access: false, reason: 'error' });
    } finally {
      setIsChecking(false);
    }
  };

  const latestCreditBundle = accessStatus?.latest_credit?.bundle;
  const canUseExistingCredit = isPro || latestCreditBundle === bundle;

  const handleCheckout = async () => {
    setIsCheckingOut(true);
    setError(null);
    try {
      const { data } = await axios.post(
        `${API}/exports/purchase-single`,
        {
          origin_url: window.location.origin,
          params,
          bundle,
          commercial_license: commercial,
          design_name: designName,
        },
        { withCredentials: true }
      );
      if (data?.url) window.location.href = data.url;
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start checkout');
      setIsCheckingOut(false);
    }
  };

  const handleGenerateExport = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const { data } = await axios.post(
        `${API}/exports/generate`,
        { params, design_name: designName, bundle },
        { withCredentials: true }
      );
      setExportResult(data);
      checkAccess(); // refresh credit count
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate export files');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = (fileType) => {
    if (exportResult?.files?.[fileType]) {
      const filePath = exportResult.files[fileType];
      const fileUrl = filePath.startsWith('http') ? filePath : `${API_ORIGIN}${filePath}`;
      window.open(fileUrl, '_blank');
    }
  };

  const handleClose = () => {
    setExportResult(null);
    setError(null);
    setShareLink(null);
    setShareCopied(false);
    onClose();
  };

  const handleShareQuote = async () => {
    setIsSharing(true);
    setError(null);
    try {
      const { data } = await axios.post(`${API}/pricing/share`, {
        params,
        bundle,
        commercial_license: commercial,
        design_name: designName,
      });
      // Always present the link on the public frontend host the user is actually on
      const fullUrl = `${window.location.origin}/quote/${data.slug}`;
      const pdfUrl = `${API_ORIGIN}/api/pricing/shared/${data.slug}/pdf`;
      setShareLink({ url: fullUrl, pdf_url: pdfUrl, slug: data.slug });
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create share link');
    } finally {
      setIsSharing(false);
    }
  };

  const copyShareLink = async () => {
    if (!shareLink?.url) return;
    try {
      await navigator.clipboard.writeText(shareLink.url);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    } catch {
      setShareCopied(false);
    }
  };

  const bundles = useMemo(() => catalog?.bundles || [], [catalog]);
  const includedFiles = useMemo(() => {
    const b = bundles.find((x) => x.key === bundle);
    return b?.files || ['dxf'];
  }, [bundles, bundle]);

  // ---- Unauthenticated state ----
  if (!isAuthenticated) {
    return (
      <Dialog open={isOpen} onOpenChange={handleClose}>
        <DialogContent className="neu-surface max-w-md" data-testid="export-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Download size={24} className="text-[var(--primary)]" />
              Export CNC Files
            </DialogTitle>
            <DialogDescription>Sign in to buy and download DXF, SVG, PDF and NC reference file bundles.</DialogDescription>
          </DialogHeader>
          <div className="py-4 text-center">
            <Button
              onClick={() => navigate('/auth', { state: { from: { pathname: '/designer' } } })}
              className="btn-primary"
              data-testid="export-signin-btn"
            >
              Sign In to Continue
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="neu-surface max-w-2xl max-h-[90vh] overflow-auto" data-testid="export-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download size={24} className="text-[var(--primary)]" />
            Export CNC Files
          </DialogTitle>
          <DialogDescription>
            Choose a bundle, review your live quote, and generate reference files for CAM verification.
          </DialogDescription>
        </DialogHeader>

        {/* ---- Success: files generated ---- */}
        {exportResult && (
          <div className="py-4" data-testid="export-success-section">
            <div className="flex items-center gap-2 text-green-500 mb-4">
              <CheckCircle size={24} weight="fill" />
              <span className="font-bold">Files generated - ready to download</span>
            </div>
            <div className="space-y-2 mb-4">
              {Object.keys(exportResult.files || {}).map((ft) => {
                const meta = FILE_META[ft] || { Icon: FileCode, label: ft, color: 'text-gray-500', hint: '' };
                const Icon = meta.Icon;
                return (
                  <button
                    key={ft}
                    onClick={() => handleDownload(ft)}
                    className="w-full flex items-center justify-between p-3 neu-surface rounded-lg hover:bg-[var(--surface-elevated)] transition-all"
                    data-testid={`download-${ft}-btn`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon size={22} className={meta.color} />
                      <div className="text-left">
                        <p className="font-bold">{meta.label}</p>
                        <p className="text-xs text-[var(--text-secondary)]">{meta.hint}</p>
                      </div>
                    </div>
                    <Download size={18} />
                  </button>
                );
              })}
            </div>
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-sm">
              <div className="flex items-start gap-2">
                <Warning size={18} className="text-yellow-500 mt-0.5 flex-shrink-0" />
                <p className="text-[var(--text-secondary)]">{exportResult.disclaimer}</p>
              </div>
            </div>
          </div>
        )}

        {/* ---- Main configurator ---- */}
        {!exportResult && (
          <div className="py-3 space-y-5">
            {/* Bundle selector */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-bold">Export bundle</label>
                {isPro && (
                  <span className="badge-pro flex items-center gap-1 text-xs">
                    <Crown size={12} /> Pro Unlimited
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2" data-testid="bundle-selector">
                {bundles.map((b) => (
                  <button
                    key={b.key}
                    onClick={() => setBundle(b.key)}
                    data-testid={`bundle-opt-${b.key}`}
                    className={`text-left p-3 rounded-lg border-2 transition-all ${
                      bundle === b.key
                        ? 'border-[var(--primary)] bg-[var(--primary)]/5'
                        : 'border-[var(--border)] hover:border-[var(--primary)]/40'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-sm">{b.label}</span>
                      {b.multiplier !== 1 && (
                        <span className="text-xs text-[var(--text-secondary)]">×{b.multiplier}</span>
                      )}
                    </div>
                    <div className="flex gap-1 flex-wrap">
                      {b.files.map((f) => (
                        <span key={f} className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 bg-[var(--surface-elevated)] rounded">
                          {f}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Commercial license toggle */}
            <label className="flex items-start gap-3 p-3 rounded-lg neu-surface cursor-pointer" data-testid="commercial-license-toggle">
              <input
                type="checkbox"
                checked={commercial}
                onChange={(e) => setCommercial(e.target.checked)}
                className="mt-1"
                data-testid="commercial-license-input"
              />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm">Commercial-use license</span>
                  <span className="text-xs text-[var(--text-secondary)]">
                    +${catalog?.constants?.commercial_license_fee ?? 29} NZD
                  </span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  Permits selling desks built from these files.
                </p>
              </div>
            </label>

            {/* Live quote breakdown */}
            <div className="rounded-lg border-2 border-[var(--primary)]/30 p-4 bg-[var(--primary)]/5" data-testid="live-quote-card">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Info size={18} className="text-[var(--primary)]" />
                  <span className="font-bold">Your live quote</span>
                </div>
                {quoteLoading && (
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                    <Spinner size={16} className="text-[var(--primary)]" />
                  </motion.div>
                )}
              </div>

              {quote ? (
                <>
                  <p className="text-sm text-[var(--text-secondary)] mb-3" data-testid="quote-headline">
                    {quote.headline}
                  </p>
                  <ul className="space-y-1.5 mb-3 text-sm">
                    {quote.line_items.map((li, idx) => (
                      <li key={idx} className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <span>{li.label}</span>
                          {li.detail && (
                            <span className="block text-xs text-[var(--text-secondary)]">{li.detail}</span>
                          )}
                        </div>
                        <span className="font-mono tabular-nums">
                          {li.amount >= 0 ? '+' : ''}${li.amount.toFixed(2)}
                        </span>
                      </li>
                    ))}
                  </ul>
                  <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
                    <span className="font-bold">Total</span>
                    <span className="text-2xl font-bold text-[var(--primary)]" data-testid="quote-total">
                      ${quote.total} <span className="text-sm font-normal">NZD</span>
                    </span>
                  </div>

                  {quote.material_note && (
                    <div
                      className="mt-3 text-xs text-[var(--text-secondary)] bg-yellow-500/10 border border-yellow-500/30 rounded-md px-3 py-2 flex items-start gap-2"
                      data-testid="material-note"
                    >
                      <Info size={14} className="mt-0.5 flex-shrink-0 text-yellow-500" />
                      <span>{quote.material_note}</span>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-[var(--text-secondary)]">Calculating...</p>
              )}
            </div>

            {/* Action area */}
            {isChecking ? (
              <div className="text-center py-4 text-[var(--text-secondary)]">Checking access...</div>
            ) : isPro ? (
              <Button
                onClick={handleGenerateExport}
                disabled={isGenerating || !quote}
                className="w-full btn-primary"
                data-testid="generate-export-btn"
              >
                {isGenerating ? 'Generating files...' : (
                  <><Crown size={16} className="mr-2" /> Generate files (Pro, included)</>
                )}
              </Button>
            ) : canUseExistingCredit ? (
              <Button
                onClick={handleGenerateExport}
                disabled={isGenerating || !quote}
                className="w-full btn-primary"
                data-testid="use-credit-btn"
              >
                {isGenerating ? 'Generating files...' : 'Use paid credit to generate files'}
              </Button>
            ) : (
              <Button
                onClick={handleCheckout}
                disabled={isCheckingOut || !quote}
                className="w-full btn-primary"
                data-testid="checkout-btn"
              >
                {isCheckingOut ? (
                  <>Redirecting to checkout...</>
                ) : (
                  <>
                    <Lock size={16} className="mr-2" />
                    {quote ? `Pay $${quote.total} NZD and download` : 'Continue to payment'}
                    <ArrowRight size={16} className="ml-2" />
                  </>
                )}
              </Button>
            )}

            {accessStatus?.remaining > 0 && !isPro && !canUseExistingCredit && (
              <p className="text-xs text-center text-[var(--text-secondary)]" data-testid="credit-mismatch-note">
                You have a paid credit for <strong>{latestCreditBundle}</strong>. Switch bundle above to use it.
              </p>
            )}

            {/* Share quote */}
            <div className="pt-3 border-t border-[var(--border)]">
              {!shareLink ? (
                <Button
                  variant="outline"
                  onClick={handleShareQuote}
                  disabled={isSharing || !quote}
                  className="w-full"
                  data-testid="share-quote-btn"
                >
                  {isSharing ? (
                    <>Preparing link...</>
                  ) : (
                    <><Share size={16} className="mr-2" /> Share this quote</>
                  )}
                </Button>
              ) : (
                <div className="space-y-2" data-testid="share-quote-result">
                  <div className="flex items-center gap-2 p-2.5 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)]">
                    <input
                      readOnly
                      value={shareLink.url}
                      className="flex-1 bg-transparent text-xs font-mono outline-none"
                      data-testid="share-link-input"
                      onFocus={(e) => e.target.select()}
                    />
                    <button
                      onClick={copyShareLink}
                      className="p-1.5 rounded hover:bg-[var(--surface)]"
                      title="Copy link"
                      data-testid="copy-share-link-btn"
                    >
                      {shareCopied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => window.open(shareLink.url, '_blank')}
                      data-testid="open-share-link-btn"
                    >
                      Open quote page
                    </Button>
                    <Button
                      variant="outline"
                      className="flex-1"
                      onClick={() => window.open(shareLink.pdf_url, '_blank')}
                      data-testid="download-quote-pdf-btn"
                    >
                      <FilePdf size={16} className="mr-2" /> PDF
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400" data-testid="export-error">
                {error}
              </div>
            )}

            <p className="text-xs text-center text-[var(--text-secondary)]">
              Includes: {includedFiles.map((f) => (FILE_META[f]?.label || f)).join(' + ')} · Files expire 24h after generation · Verify in CAM before cutting
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ExportDialog;
