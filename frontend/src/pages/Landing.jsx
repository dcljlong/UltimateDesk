import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Cube,
  Download,
  Lightning,
  ArrowRight,
  Check,
  Sun,
  Moon,
  Ruler,
  Package,
  TreeStructure
} from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
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
const API = getApiUrl();

const Landing = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [presets, setPresets] = useState([]);

  useEffect(() => {
    const fetchPresets = async () => {
      try {
        const { data } = await axios.get(`${API}/designs/presets`);
        setPresets(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error('Failed to fetch presets:', error);
      }
    };
    fetchPresets();
  }, []);

  const features = [
    {
      icon: <Cube size={32} weight="fill" />,
      title: 'Export-aligned 3D Preview',
      description: 'Preview the same straight-frame desk family that drives the exported build pack.'
    },
    {
      icon: <TreeStructure size={32} weight="fill" />,
      title: 'Live Nesting + Toolpath',
      description: 'See sheet layout, parts count and reference toolpath inside the designer.'
    },
    {
      icon: <Download size={32} weight="fill" />,
      title: 'DXF, SVG, PDF and NC Exports',
      description: 'Generate reference CNC files and cut-sheet references from the current saved design.'
    },
    {
      icon: <Lightning size={32} weight="fill" />,
      title: 'NZ Sheet Ready',
      description: 'Built around 2400 x 1200 sheets and 18mm plywood for Kiwi maker workflows.'
    }
  ];

  const provenAddons = [
    'Cable tray',
    'Mixer tray',
    'Headset hook',
    'VESA mount'
  ];

  const handleGetStarted = () => {
    if (isAuthenticated) {
      navigate('/designer');
    } else {
      navigate('/auth');
    }
  };

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="fixed top-0 left-0 right-0 z-50 glass-surface">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <Cube size={32} weight="fill" className="text-[var(--primary)]" />
              <span className="text-xl font-bold tracking-tight">UltimateDesk</span>
              <span className="badge-pro ml-2">Straight Frame</span>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg neu-surface transition-smooth"
                data-testid="theme-toggle-btn"
              >
                {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
              </button>
              {isAuthenticated ? (
                <Button onClick={() => navigate('/designer')} data-testid="nav-designer-btn">
                  Open Designer
                </Button>
              ) : (
                <Button onClick={() => navigate('/auth')} data-testid="nav-login-btn">
                  Sign In
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[var(--surface)] to-[var(--background)]" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-4xl mx-auto"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full neu-surface mb-6">
              <Package size={16} className="text-[var(--primary)]" />
              <span className="text-sm font-medium">Commercial straight-frame desk builder</span>
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter mb-6">
              Design the Desk.
              <br />
              <span className="text-[var(--primary)]">Export the Build Pack.</span>
            </h1>

            <p className="text-lg sm:text-xl text-[var(--text-secondary)] mb-8 max-w-3xl mx-auto">
              Configure a proven straight-frame desk, preview the real build, check live nesting,
              and export DXF, SVG, PDF and NC files for CNC workflows.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                size="lg"
                onClick={handleGetStarted}
                className="btn-primary text-lg px-8 py-4"
                data-testid="get-started-btn"
              >
                Open Designer <ArrowRight size={20} className="ml-2" />
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={() => navigate('/pricing')}
                className="btn-secondary text-lg px-8 py-4"
                data-testid="view-pricing-btn"
              >
                View Export Pricing
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter mb-4">
              What the current product actually does
            </h2>
            <p className="text-[var(--text-secondary)] text-lg">
              Built around one honest desk family with real export proof
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className="neu-surface p-6 transition-smooth hover:translate-y-[-4px]"
              >
                <div className="text-[var(--primary)] mb-4">{feature.icon}</div>
                <h3 className="text-xl font-bold mb-2">{feature.title}</h3>
                <p className="text-[var(--text-secondary)] text-sm">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 bg-[var(--surface)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter mb-4">
              Proven add-ons
            </h2>
            <p className="text-[var(--text-secondary)] text-lg">
              Feature toggles already proven through export output
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="neu-surface p-8">
              <h3 className="text-2xl font-bold mb-4">Base desk family</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2"><Check size={16} className="text-[var(--success)]" /> Straight-frame build</div>
                <div className="flex items-center gap-2"><Check size={16} className="text-[var(--success)]" /> Live size controls</div>
                <div className="flex items-center gap-2"><Check size={16} className="text-[var(--success)]" /> Live nesting + toolpath preview</div>
                <div className="flex items-center gap-2"><Check size={16} className="text-[var(--success)]" /> DXF, SVG, PDF, NC export flow</div>
              </div>
            </div>

            <div className="neu-surface p-8">
              <h3 className="text-2xl font-bold mb-4">Current add-ons</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {provenAddons.map((item) => (
                  <div key={item} className="flex items-center gap-2">
                    <Check size={16} className="text-[var(--success)]" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
              <div className="mt-6 flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                <Ruler size={16} />
                2400 x 1200 / 18mm workflow
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter mb-4">
              Start with a template
            </h2>
            <p className="text-[var(--text-secondary)] text-lg">
              Open a preset, then configure and export from the designer
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {presets.map((preset, index) => (
              <motion.div
                key={preset.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: index * 0.1 }}
                className="neu-surface overflow-hidden group cursor-pointer transition-smooth hover:translate-y-[-4px]"
                onClick={() => navigate(`/designer?preset=${preset.id}`)}
                data-testid={`preset-card-${preset.id}`}
              >
                <div className="h-48 bg-gradient-to-br from-[var(--surface-elevated)] to-[var(--surface)] relative overflow-hidden">
                  <div className="absolute inset-0 grid-pattern" />
                  <div className="absolute bottom-4 left-4">
                    <span className="text-6xl font-black text-[var(--primary)] opacity-20">
                      {preset.params.width}
                    </span>
                  </div>
                </div>
                <div className="p-6">
                  <h3 className="text-xl font-bold mb-2">{preset.name}</h3>
                  <p className="text-[var(--text-secondary)] text-sm mb-4">{preset.description}</p>
                  <div className="flex items-center gap-2 text-sm font-mono text-[var(--text-secondary)]">
                    <span>{preset.params.width}mm</span>
                    <span>x</span>
                    <span>{preset.params.depth}mm</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="neu-surface p-8 md:p-12 text-center relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--primary)] opacity-10 rounded-full blur-3xl" />
            <span className="badge-pro mb-4 inline-block">Export</span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter mb-4">
              Free to configure. Pay when you export.
            </h2>
            <p className="text-[var(--text-secondary)] text-lg mb-6 max-w-xl mx-auto">
              Design, preview, nest and review the build inside the app. Use the export flow for file pricing and download options.
            </p>
            <ul className="text-left space-y-2 mb-6 inline-block">
              {[
                'Straight-frame desk family',
                'Live nesting and reference toolpath',
                'DXF, SVG, PDF and NC output',
                'Saved designs and reusable presets'
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <Check size={16} className="text-[var(--success)]" />
                  {item}
                </li>
              ))}
            </ul>
            <div>
              <Button
                size="lg"
                onClick={() => navigate('/pricing')}
                className="btn-primary"
                data-testid="upgrade-pro-btn"
              >
                View Pricing
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      <footer className="py-8 border-t border-[var(--border)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Cube size={24} weight="fill" className="text-[var(--primary)]" />
              <span className="font-bold">UltimateDesk</span>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">
              Straight-frame commercial desk builder for Kiwi makers.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;

