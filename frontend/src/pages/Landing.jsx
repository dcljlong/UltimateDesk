import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Cube, 
  ChatCircle, 
  Download, 
  Lightning, 
  ArrowRight,
  Check,
  Sun,
  Moon
} from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import axios from 'axios';

const getApiUrl = () => {
  // Use window.location.origin to ensure same protocol
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return window.location.origin + '/api';
  }
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  return baseUrl + '/api';
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
        setPresets(data);
      } catch (error) {
        console.error('Failed to fetch presets:', error);
      }
    };
    fetchPresets();
  }, []);

  const features = [
    {
      icon: <ChatCircle size={32} weight="fill" />,
      title: "AI Chat Designer",
      description: "Describe your dream desk in plain English. Our AI understands gaming setups, studio rigs, and office needs."
    },
    {
      icon: <Cube size={32} weight="fill" />,
      title: "3D Preview",
      description: "See your desk in stunning 3D. Rotate, explode, and visualize every finger joint before cutting."
    },
    {
      icon: <Download size={32} weight="fill" />,
      title: "CNC Ready Files",
      description: "Export optimized DXF, G-code, and cutting sheets. Under 5% material waste guaranteed."
    },
    {
      icon: <Lightning size={32} weight="fill" />,
      title: "NZ Optimized",
      description: "Designed for 2400x1200mm NZ plywood sheets. 18mm thickness, hobby CNC compatible."
    }
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
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass-surface">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <Cube size={32} weight="fill" className="text-[var(--primary)]" />
              <span className="text-xl font-bold tracking-tight">UltimateDesk</span>
              <span className="badge-pro ml-2">CNC Pro</span>
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

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div 
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `url(https://images.unsplash.com/photo-1603481618010-21dd9adb7d1d?w=1920&q=80)`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            filter: 'brightness(0.3)'
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[var(--background)]/80 to-[var(--background)]" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-4xl mx-auto"
          >
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter mb-6">
              Design Your Perfect Desk.
              <br />
              <span className="text-[var(--primary)]">Cut It Yourself.</span>
            </h1>
            <p className="text-lg sm:text-xl text-[var(--text-secondary)] mb-8 max-w-2xl mx-auto">
              AI-powered desk designer for Kiwi makers. From gaming battlestations to music production studios. 
              Generate CNC-ready files from 18mm NZ plywood.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button 
                size="lg" 
                onClick={handleGetStarted}
                className="btn-primary text-lg px-8 py-4"
                data-testid="get-started-btn"
              >
                Start Designing <ArrowRight size={20} className="ml-2" />
              </Button>
              <Button 
                variant="outline" 
                size="lg"
                onClick={() => navigate('/pricing')}
                className="btn-secondary text-lg px-8 py-4"
                data-testid="view-pricing-btn"
              >
                View Pricing
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter mb-4">
              Everything You Need to Build
            </h2>
            <p className="text-[var(--text-secondary)] text-lg">
              From concept to CNC-ready in minutes
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

      {/* Presets Section */}
      <section className="py-20 bg-[var(--surface)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter mb-4">
              Start with a Template
            </h2>
            <p className="text-[var(--text-secondary)] text-lg">
              Optimized presets for every use case
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
                <div 
                  className="h-48 bg-gradient-to-br from-[var(--surface-elevated)] to-[var(--surface)] relative overflow-hidden"
                >
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

      {/* Pricing CTA */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="neu-surface p-8 md:p-12 text-center relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--primary)] opacity-10 rounded-full blur-3xl" />
            <span className="badge-pro mb-4 inline-block">Pro</span>
            <h2 className="text-3xl sm:text-4xl font-black tracking-tighter mb-4">
              Unlock CNC Exports
            </h2>
            <p className="text-[var(--text-secondary)] text-lg mb-6 max-w-xl mx-auto">
              Free to design and preview. Upgrade to Pro for G-code, DXF, and optimized cutting sheets.
            </p>
            <div className="flex flex-col items-center gap-4">
              <div className="text-4xl font-black">
                $4.99 <span className="text-lg font-normal text-[var(--text-secondary)]">NZD/month</span>
              </div>
              <ul className="text-left space-y-2 mb-6">
                {[
                  'Unlimited design exports',
                  'G-code for 6mm, 8mm, 12mm bits',
                  'Optimized nesting (<5% waste)',
                  'DXF, SVG, PDF downloads'
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <Check size={16} className="text-[var(--success)]" />
                    {item}
                  </li>
                ))}
              </ul>
              <Button 
                size="lg" 
                onClick={() => navigate('/pricing')}
                className="btn-primary"
                data-testid="upgrade-pro-btn"
              >
                Upgrade to Pro
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-[var(--border)]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Cube size={24} weight="fill" className="text-[var(--primary)]" />
              <span className="font-bold">UltimateDesk CNC Pro</span>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">
              Made for Kiwi makers. Designed in New Zealand.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
