import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Download, 
  X, 
  Crown, 
  FileCode, 
  Cube, 
  FilePdf,
  Warning,
  Check,
  Spinner,
  ArrowRight
} from '@phosphor-icons/react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const getApiUrl = () => {
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return window.location.origin + '/api';
  }
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  return baseUrl + '/api';
};
const API = getApiUrl();

const ExportDialog = ({ isOpen, onClose, params, designName }) => {
  const { isAuthenticated, isPro } = useAuth();
  const navigate = useNavigate();
  
  const [accessStatus, setAccessStatus] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [exportResult, setExportResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && isAuthenticated) {
      checkAccess();
    }
  }, [isOpen, isAuthenticated]);

  const checkAccess = async () => {
    setIsChecking(true);
    try {
      const { data } = await axios.post(`${API}/exports/check-access`, {}, { withCredentials: true });
      setAccessStatus(data);
    } catch (error) {
      console.error('Access check error:', error);
      setAccessStatus({ has_access: false, reason: 'error' });
    } finally {
      setIsChecking(false);
    }
  };

  const handleGenerateExport = async () => {
    setIsGenerating(true);
    setError(null);
    
    try {
      const { data } = await axios.post(
        `${API}/exports/generate`,
        { params, design_name: designName },
        { withCredentials: true }
      );
      setExportResult(data);
    } catch (error) {
      console.error('Export error:', error);
      setError(error.response?.data?.detail || 'Failed to generate export files');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = (fileType) => {
    if (exportResult?.files?.[fileType]) {
      window.open(`${API}${exportResult.files[fileType]}`, '_blank');
    }
  };

  const handleClose = () => {
    setExportResult(null);
    setError(null);
    onClose();
  };

  // Not authenticated
  if (!isAuthenticated) {
    return (
      <Dialog open={isOpen} onOpenChange={handleClose}>
        <DialogContent className="neu-surface max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Download size={24} className="text-[var(--primary)]" />
              Export CNC Files
            </DialogTitle>
          </DialogHeader>
          
          <div className="py-6 text-center">
            <p className="text-[var(--text-secondary)] mb-6">
              Sign in to export your desk designs as production-ready CNC files.
            </p>
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
      <DialogContent className="neu-surface max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download size={24} className="text-[var(--primary)]" />
            Export CNC Files
          </DialogTitle>
        </DialogHeader>

        {/* Checking access */}
        {isChecking && (
          <div className="py-8 text-center">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="inline-block"
            >
              <Spinner size={32} className="text-[var(--primary)]" />
            </motion.div>
            <p className="mt-4 text-[var(--text-secondary)]">Checking access...</p>
          </div>
        )}

        {/* Export result */}
        {exportResult && !isChecking && (
          <div className="py-4">
            <div className="flex items-center gap-2 text-[var(--success)] mb-4">
              <Check size={24} weight="bold" />
              <span className="font-bold">Files Generated Successfully!</span>
            </div>
            
            {/* Download buttons */}
            <div className="space-y-3 mb-6">
              <button
                onClick={() => handleDownload('dxf')}
                className="w-full flex items-center justify-between p-4 neu-surface rounded-lg hover:bg-[var(--surface-elevated)] transition-all"
                data-testid="download-dxf-btn"
              >
                <div className="flex items-center gap-3">
                  <FileCode size={24} className="text-blue-500" />
                  <div className="text-left">
                    <p className="font-bold">DXF File</p>
                    <p className="text-xs text-[var(--text-secondary)]">CAD/CAM ready geometry</p>
                  </div>
                </div>
                <Download size={20} />
              </button>

              <button
                onClick={() => handleDownload('gcode')}
                className="w-full flex items-center justify-between p-4 neu-surface rounded-lg hover:bg-[var(--surface-elevated)] transition-all"
                data-testid="download-gcode-btn"
              >
                <div className="flex items-center gap-3">
                  <Cube size={24} className="text-green-500" />
                  <div className="text-left">
                    <p className="font-bold">G-Code File</p>
                    <p className="text-xs text-[var(--text-secondary)]">CNC machine instructions</p>
                  </div>
                </div>
                <Download size={20} />
              </button>

              <button
                onClick={() => handleDownload('pdf')}
                className="w-full flex items-center justify-between p-4 neu-surface rounded-lg hover:bg-[var(--surface-elevated)] transition-all"
                data-testid="download-pdf-btn"
              >
                <div className="flex items-center gap-3">
                  <FilePdf size={24} className="text-red-500" />
                  <div className="text-left">
                    <p className="font-bold">Cutting Sheet (HTML)</p>
                    <p className="text-xs text-[var(--text-secondary)]">Visual parts reference</p>
                  </div>
                </div>
                <Download size={20} />
              </button>
            </div>

            {/* Disclaimer */}
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <Warning size={20} className="text-yellow-500 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-bold text-yellow-600 mb-1">Safety Reminder</p>
                  <p className="text-[var(--text-secondary)]">
                    {exportResult.disclaimer || 'Verify all toolpaths in your CAM software before cutting.'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Has access - show generate button */}
        {accessStatus?.has_access && !exportResult && !isChecking && (
          <div className="py-4">
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-2">
                {isPro ? (
                  <span className="badge-pro flex items-center gap-1">
                    <Crown size={12} /> Pro Unlimited
                  </span>
                ) : (
                  <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded-full text-xs font-medium">
                    {accessStatus.remaining} export{accessStatus.remaining !== 1 ? 's' : ''} remaining
                  </span>
                )}
              </div>
              <p className="text-sm text-[var(--text-secondary)]">
                Generate production-ready files for <strong>{designName}</strong>
              </p>
            </div>

            {/* File types preview */}
            <div className="grid grid-cols-3 gap-3 mb-6">
              <div className="text-center p-3 neu-surface rounded-lg">
                <FileCode size={28} className="mx-auto text-blue-500 mb-1" />
                <p className="text-xs font-medium">DXF</p>
              </div>
              <div className="text-center p-3 neu-surface rounded-lg">
                <Cube size={28} className="mx-auto text-green-500 mb-1" />
                <p className="text-xs font-medium">G-Code</p>
              </div>
              <div className="text-center p-3 neu-surface rounded-lg">
                <FilePdf size={28} className="mx-auto text-red-500 mb-1" />
                <p className="text-xs font-medium">PDF</p>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <Button
              onClick={handleGenerateExport}
              disabled={isGenerating}
              className="w-full btn-primary"
              data-testid="generate-export-btn"
            >
              {isGenerating ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="mr-2"
                  >
                    <Spinner size={18} />
                  </motion.div>
                  Generating Files...
                </>
              ) : (
                <>
                  <Download size={18} className="mr-2" />
                  Generate Export Package
                </>
              )}
            </Button>
          </div>
        )}

        {/* No access - show purchase options */}
        {accessStatus && !accessStatus.has_access && !isChecking && (
          <div className="py-4">
            <div className="text-center mb-6">
              <Crown size={48} className="mx-auto text-[var(--primary)] mb-3" />
              <h3 className="font-bold text-lg mb-2">Unlock Pro Exports</h3>
              <p className="text-sm text-[var(--text-secondary)]">
                Get production-ready DXF, G-Code, and PDF files for your designs.
              </p>
            </div>

            <div className="space-y-3">
              <button
                onClick={() => navigate('/pricing')}
                className="w-full flex items-center justify-between p-4 border-2 border-blue-500 rounded-lg hover:bg-blue-500/10 transition-all"
                data-testid="buy-single-export-btn"
              >
                <div className="text-left">
                  <p className="font-bold">Single Export</p>
                  <p className="text-xs text-[var(--text-secondary)]">One-time purchase</p>
                </div>
                <div className="text-right">
                  <p className="font-bold text-blue-500">$4.99 NZD</p>
                </div>
              </button>

              <button
                onClick={() => navigate('/pricing')}
                className="w-full flex items-center justify-between p-4 border-2 border-[var(--primary)] rounded-lg hover:bg-[var(--primary)]/10 transition-all"
                data-testid="buy-pro-btn"
              >
                <div className="text-left flex items-center gap-2">
                  <Crown size={20} className="text-[var(--primary)]" />
                  <div>
                    <p className="font-bold">Pro Unlimited</p>
                    <p className="text-xs text-[var(--text-secondary)]">Best value</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-[var(--primary)]">$19/mo</p>
                </div>
              </button>
            </div>

            <Button
              variant="outline"
              className="w-full mt-4"
              onClick={() => navigate('/pricing')}
            >
              View All Pricing Options <ArrowRight size={16} className="ml-2" />
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ExportDialog;
