import { useState } from 'react';
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
  Lightning,
  Download,
  FileCode,
  FilePdf,
  Cube as CubeIcon,
  Package,
  TreeStructure
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
    { text: 'Straight-frame desk builder', included: true },
    { text: 'Export-aligned 3D preview', included: true },
    { text: 'Live nesting layout', included: true },
    { text: 'Reference toolpath preview', included: true },
    { text: 'Save unlimited designs', included: true },
    { text: 'Start from presets', included: true },
    { text: 'Proven add-ons: cable tray, mixer tray, hook, VESA', included: true },
    { text: 'DXF, SVG, PDF and NC downloads', included: false },
    { text: 'Paid export bundles', included: false },
    { text: 'Unlimited paid exports', included: false },
  ];

  const singleFeatures = [
    { text: 'Everything in Free', included: true },
    { text: 'Open designer and see live price before checkout', included: true },
    { text: 'Choose your bundle per design', included: true },
    { text: 'DXF only through full pack options', included: true },
    { text: 'DXF, SVG, PDF and NC when included in bundle', included: true },
    { text: 'Optional commercial-use license', included: true },
    { text: 'Good for one-off builds or testing designs', included: true },
    { text: 'Files valid for 24 hours', included: true },
  ];

  const proFeatures = [
    { text: 'Everything in Free', included: true },
    { text: 'Generate export bundles for every design while subscribed', included: true },
    { text: 'DXF, SVG, PDF and NC for every design', included: true },
    { text: 'No per-design checkout for subscribed accounts', included: true },
    { text: 'Generate export bundles for every design while subscribed', included: true },
    { text: 'No per-design checkout for subscribed accounts', included: true },
    { text: 'Best for repeat makers and commercial workflows', included: true },
  ];

  return (
    <div className="min-h-screen bg-[var(--background)]">
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

      <main className="max-w-6xl mx-auto px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full neu-surface mb-6">
            <Package size={16} className="text-[var(--primary)]" />
            <span className="text-sm font-medium">Straight-frame commercial desk builder</span>
          </div>

          <h1 className="text-4xl sm:text-5xl font-black tracking-tighter mb-4">
            Configure Free.
            <br />
            <span className="text-[var(--primary)]">Pay When You Export.</span>
          </h1>

          <p className="text-lg text-[var(--text-secondary)] max-w-3xl mx-auto">
            Build a proven straight-frame desk, review live nesting and reference toolpath,
            then choose the export option that fits your job.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex flex-wrap justify-center gap-4 mb-12"
        >
          <div className="flex items-center gap-2 px-4 py-2 neu-surface rounded-lg">
            <FileCode size={22} className="text-blue-500" />
            <span className="font-mono text-sm">DXF / SVG</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 neu-surface rounded-lg">
            <CubeIcon size={22} className="text-green-500" />
            <span className="font-mono text-sm">NC</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 neu-surface rounded-lg">
            <FilePdf size={22} className="text-red-500" />
            <span className="font-mono text-sm">PDF Cut Sheet</span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 neu-surface rounded-lg">
            <TreeStructure size={22} className="text-[var(--primary)]" />
            <span className="font-mono text-sm">Live Nesting</span>
          </div>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="neu-surface p-6 rounded-xl"
          >
            <div className="flex items-center gap-2 mb-4">
              <Package size={24} className="text-[var(--text-secondary)]" />
              <h2 className="text-xl font-bold">Free Builder</h2>
            </div>
            <div className="mb-4">
              <span className="text-3xl font-black">$0</span>
              <span className="text-[var(--text-secondary)]"> / forever</span>
            </div>
            <p className="text-[var(--text-secondary)] text-sm mb-6">
              Configure, preview, save and review build layout inside the app.
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
              Open Builder
            </Button>
          </motion.div>

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
              <span className="text-3xl font-black">from $22</span>
              <span className="text-[var(--text-secondary)]"> NZD</span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mb-4">
              Best for one-off jobs, design testing, and occasional builds.
            </p>

            <ul className="space-y-2 mb-6 text-sm">
              {singleFeatures.map((feature, idx) => (
                <li key={idx} className="flex items-start gap-2">
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
              Open Designer & See Price
            </Button>
          </motion.div>

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
              <span className="text-[var(--text-secondary)]"> NZD / month</span>
            </div>
            <p className="text-[var(--text-secondary)] text-sm mb-6">
              Unlimited exports for repeat makers and commercial workflows.
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
              <Button className="w-full btn-secondary" disabled>
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

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-12 max-w-3xl mx-auto"
        >
          <div className="neu-surface p-6 rounded-xl">
            <h3 className="font-bold mb-2 flex items-center gap-2">
              <span className="text-yellow-500">⚠</span>
              Important safety note
            </h3>
            <p className="text-sm text-[var(--text-secondary)]">
              Exports are reference files for real-world CNC workflows. Always verify dimensions,
              nesting, tooling and CAM toolpaths before cutting material.
            </p>
            <p className="text-xs text-[var(--text-secondary)] mt-3">
              If checkout, file access, or export generation does not work as expected, contact
              support@ultimatedesk.co.nz. We will help resolve access issues, reissue available
              files where practical, or review the transaction. Nothing here limits any rights
              you may have under applicable consumer law.
            </p>
          </div>
        </motion.div>
      </main>
    </div>
  );
};

export default Pricing;
