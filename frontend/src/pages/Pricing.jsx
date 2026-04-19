import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Cube, 
  Check, 
  X, 
  Sun, 
  Moon,
  CaretLeft,
  Crown,
  Rocket,
  Lightning,
  Download,
  FileCode,
  FilePdf,
  Cube as CubeIcon
} from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import axios from 'axios';

const getApiUrl = () => {
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return window.location.origin + '/api';
  }
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  return baseUrl + '/api';
};
const API = getApiUrl();

const Pricing = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isPro } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isLoadingSingle, setIsLoadingSingle] = useState(false);
  const [isLoadingPro, setIsLoadingPro] = useState(false);

  const handlePurchaseSingle = () => {
    navigate('/designer');
  };

  const handlePurchasePro = async () => {
    if (!isAuthenticated) {
      navigate('/auth', { state: { from: { pathname: '/pricing' } } });
      return;
    }

    setIsLoadingPro(true);
    try {
      const { data } = await axios.post(
        `${API}/exports/purchase-pro`,
        { origin_url: window.location.origin },
        { withCredentials: true }
      );
      
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (error) {
      console.error('Checkout error:', error);
      alert('Failed to create checkout. Please try again.');
    } finally {
      setIsLoadingPro(false);
    }
  };

  const freeFeatures = [
    { text: 'Unlimited AI desk design conversations', included: true },
    { text: 'Real-time isometric preview', included: true },
    { text: 'All desk presets (Gaming, Studio, Office)', included: true },
    { text: 'Explode view & dimensions', included: true },
    { text: 'Sheet nesting preview', included: true },
    { text: 'G-Code preview (first 3 parts)', included: true },
    { text: 'Save unlimited designs', included: true },
    { text: 'Download DXF files', included: false },
    { text: 'Download full G-Code', included: false },
    { text: 'PDF cutting sheets', included: false },
  ];

  const singleFeatures = [
    { text: 'Everything in Free', included: true },
    { text: 'Pay per design — price scales with:', included: true },
    { text: '→ Material sheets required', included: true, indent: true },
    { text: '→ Part count & joint complexity', included: true, indent: true },
    { text: '→ Premium features enabled', included: true, indent: true },
    { text: 'Pick your bundle (DXF → Full Pack)', included: true },
    { text: 'Optional commercial-use license', included: true },
    { text: 'Transparent live quote before checkout', included: true },
    { text: 'Files valid for 24 hours', included: true },
  ];

  const proFeatures = [
    { text: 'Everything in Free', included: true },
    { text: 'Unlimited export packages', included: true },
    { text: 'DXF, G-Code, PDF for every design', included: true },
    { text: 'Priority file generation', included: true },
    { text: 'Files never expire', included: true },
    { text: 'Email support', included: true },
    { text: 'Early access to new features', included: true },
  ];

  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="h-16 border-b border-[var(--border)] px-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => navigate('/')}
            data-testid="nav-home-btn"
          >
            <CaretLeft size={20} />
          </Button>
          <div className="flex items-center gap-2">
            <Cube size={28} weight="fill" className="text-[var(--primary)]" />
            <span className="font-bold">Pricing</span>
          </div>
        </div>

        <Button 
          variant="ghost" 
          size="icon"
          onClick={toggleTheme}
          data-testid="theme-toggle"
        >
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </Button>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl sm:text-5xl font-black tracking-tighter mb-4">
            Design Free. Pay Only to Cut.
          </h1>
          <p className="text-lg text-[var(--text-secondary)] max-w-2xl mx-auto">
            Create unlimited designs for free. Export production-ready CNC files when you're ready to build.
          </p>
        </motion.div>

        {/* Export file types showcase */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex justify-center gap-6 mb-12"
        >
          <div className="flex items-center gap-2 px-4 py-2 neu-surface rounded-lg">
            <FileCode size={24} className="text-blue-500" />
            <span className="font-mono text-sm">DXF</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 neu-surface rounded-lg">
            <CubeIcon size={24} className="text-green-500" />
            <span className="font-mono text-sm">G-Code</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 neu-surface rounded-lg">
            <FilePdf size={24} className="text-red-500" />
            <span className="font-mono text-sm">PDF</span>
          </div>
        </motion.div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {/* Free Tier */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="neu-surface p-6 rounded-xl"
          >
            <div className="flex items-center gap-2 mb-4">
              <Rocket size={24} className="text-[var(--text-secondary)]" />
              <h2 className="text-xl font-bold">Free</h2>
            </div>
            <div className="mb-4">
              <span className="text-3xl font-black">$0</span>
              <span className="text-[var(--text-secondary)]">/forever</span>
            </div>
            <p className="text-[var(--text-secondary)] text-sm mb-6">
              Design and preview unlimited desks
            </p>

            <ul className="space-y-2 mb-6 text-sm">
              {freeFeatures.map((feature, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  {feature.included ? (
                    <Check size={16} className="text-[var(--success)] mt-0.5 flex-shrink-0" />
                  ) : (
                    <X size={16} className="text-[var(--text-secondary)] mt-0.5 flex-shrink-0" />
                  )}
                  <span className={!feature.included ? 'text-[var(--text-secondary)]' : ''}>
                    {feature.text}
                  </span>
                </li>
              ))}
            </ul>

            <Button 
              variant="outline" 
              className="w-full"
              onClick={() => navigate('/designer')}
              data-testid="start-free-btn"
            >
              Start Designing
            </Button>
          </motion.div>

          {/* Per-design pricing */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="neu-surface p-6 rounded-xl border-2 border-blue-500"
          >
            <div className="flex items-center gap-2 mb-4">
              <Download size={24} className="text-blue-500" />
              <h2 className="text-xl font-bold">Per-Design Export</h2>
            </div>
            <div className="mb-1">
              <span className="text-3xl font-black">from $14</span>
              <span className="text-[var(--text-secondary)]"> NZD</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mb-4">
              Small desk, 1 sheet, simple joints: <strong>$14</strong><br />
              Large studio, 3 sheets, premium features: <strong>~$34–45</strong>
            </p>

            <ul className="space-y-2 mb-6 text-sm">
              {singleFeatures.map((feature, idx) => (
                <li key={idx} className={`flex items-start gap-2 ${feature.indent ? 'ml-4' : ''}`}>
                  <Check size={16} className="text-[var(--success)] mt-0.5 flex-shrink-0" />
                  <span>{feature.text}</span>
                </li>
              ))}
            </ul>

            <Button
              className="w-full bg-blue-500 hover:bg-blue-600 text-white"
              onClick={handlePurchaseSingle}
              data-testid="buy-single-btn"
            >
              Design & See My Price
            </Button>
          </motion.div>

          {/* Pro Tier */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="relative neu-surface p-6 rounded-xl border-2 border-[var(--primary)]"
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="badge-pro flex items-center gap-1 px-3 py-1">
                <Crown size={12} />
                Best Value
              </span>
            </div>

            <div className="flex items-center gap-2 mb-4">
              <Lightning size={24} weight="fill" className="text-[var(--primary)]" />
              <h2 className="text-xl font-bold">Pro</h2>
            </div>
            <div className="mb-4">
              <span className="text-3xl font-black">$19</span>
              <span className="text-[var(--text-secondary)]"> NZD/month</span>
            </div>
            <p className="text-[var(--text-secondary)] text-sm mb-6">
              Unlimited exports for serious makers
            </p>

            <ul className="space-y-2 mb-6 text-sm">
              {proFeatures.map((feature, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <Check size={16} className="text-[var(--success)] mt-0.5 flex-shrink-0" />
                  <span>{feature.text}</span>
                </li>
              ))}
            </ul>

            {isPro ? (
              <Button 
                className="w-full btn-secondary"
                disabled
              >
                <Check size={18} className="mr-2" />
                You're Pro!
              </Button>
            ) : (
              <Button 
                className="w-full btn-primary"
                onClick={handlePurchasePro}
                disabled={isLoadingPro}
                data-testid="buy-pro-btn"
              >
                {isLoadingPro ? 'Loading...' : 'Go Pro'}
              </Button>
            )}
          </motion.div>
        </div>

        {/* Disclaimer */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-12 max-w-3xl mx-auto"
        >
          <div className="neu-surface p-6 rounded-xl">
            <h3 className="font-bold mb-2 flex items-center gap-2">
              <span className="text-yellow-500">⚠️</span>
              Important Safety Note
            </h3>
            <p className="text-sm text-[var(--text-secondary)]">
              Export files are high-quality <strong>reference files</strong>. You must verify all toolpaths in your 
              CAM software (VCarve, Fusion 360, etc.) before cutting. UltimateDesk provides geometry-accurate 
              files but is not responsible for machine-specific settings, material variations, or toolpath validation.
            </p>
          </div>
        </motion.div>

        {/* FAQ */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-12 text-center"
        >
          <h3 className="text-xl font-bold mb-4">Questions?</h3>
          <p className="text-[var(--text-secondary)]">
            Email us at <a href="mailto:support@ultimatedesk.co.nz" className="text-[var(--primary)] hover:underline">support@ultimatedesk.co.nz</a>
          </p>
        </motion.div>
      </main>
    </div>
  );
};

export default Pricing;
