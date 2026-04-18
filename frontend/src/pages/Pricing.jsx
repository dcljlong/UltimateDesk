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
  Lightning
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

const Pricing = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isPro } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isLoading, setIsLoading] = useState(false);

  const handleUpgrade = async () => {
    if (!isAuthenticated) {
      navigate('/auth', { state: { from: { pathname: '/pricing' } } });
      return;
    }

    setIsLoading(true);
    try {
      const { data } = await axios.post(
        `${API}/payments/create-checkout`,
        { origin_url: window.location.origin },
        { withCredentials: true }
      );
      
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (error) {
      console.error('Checkout error:', error);
      alert('Failed to create checkout session. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const freeFeatures = [
    { text: 'Unlimited AI design conversations', included: true },
    { text: 'Real-time 3D preview', included: true },
    { text: 'All desk presets', included: true },
    { text: 'Explode view & dimensions', included: true },
    { text: 'Sheet nesting preview', included: true },
    { text: 'G-Code preview', included: true },
    { text: 'Download DXF files', included: false },
    { text: 'Download full G-Code', included: false },
    { text: 'PDF cutting sheets', included: false },
    { text: 'Priority support', included: false },
  ];

  const proFeatures = [
    { text: 'Unlimited AI design conversations', included: true },
    { text: 'Real-time 3D preview', included: true },
    { text: 'All desk presets', included: true },
    { text: 'Explode view & dimensions', included: true },
    { text: 'Sheet nesting preview', included: true },
    { text: 'G-Code preview', included: true },
    { text: 'Download DXF files', included: true },
    { text: 'Download full G-Code', included: true },
    { text: 'PDF cutting sheets', included: true },
    { text: 'Priority support', included: true },
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
      <main className="max-w-5xl mx-auto px-4 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl sm:text-5xl font-black tracking-tighter mb-4">
            Simple, Fair Pricing
          </h1>
          <p className="text-lg text-[var(--text-secondary)] max-w-xl mx-auto">
            Design for free. Pay only when you're ready to cut.
          </p>
        </motion.div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Tier */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="neu-surface p-8 rounded-xl"
          >
            <div className="flex items-center gap-2 mb-4">
              <Rocket size={24} className="text-[var(--text-secondary)]" />
              <h2 className="text-2xl font-bold">Free</h2>
            </div>
            <div className="mb-6">
              <span className="text-4xl font-black">$0</span>
              <span className="text-[var(--text-secondary)]">/forever</span>
            </div>
            <p className="text-[var(--text-secondary)] mb-6">
              Perfect for exploring and designing your dream desk
            </p>

            <ul className="space-y-3 mb-8">
              {freeFeatures.map((feature, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  {feature.included ? (
                    <Check size={18} className="text-[var(--success)]" />
                  ) : (
                    <X size={18} className="text-[var(--text-secondary)]" />
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

          {/* Pro Tier */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="relative neu-surface p-8 rounded-xl border-2 border-[var(--primary)]"
          >
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="badge-pro flex items-center gap-1">
                <Crown size={12} />
                Most Popular
              </span>
            </div>

            <div className="flex items-center gap-2 mb-4">
              <Lightning size={24} weight="fill" className="text-[var(--primary)]" />
              <h2 className="text-2xl font-bold">Pro</h2>
            </div>
            <div className="mb-6">
              <span className="text-4xl font-black">$4.99</span>
              <span className="text-[var(--text-secondary)]"> NZD/month</span>
            </div>
            <p className="text-[var(--text-secondary)] mb-6">
              Everything you need to bring your designs to life
            </p>

            <ul className="space-y-3 mb-8">
              {proFeatures.map((feature, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <Check size={18} className="text-[var(--success)]" />
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
                You're a Pro!
              </Button>
            ) : (
              <Button 
                className="w-full btn-primary"
                onClick={handleUpgrade}
                disabled={isLoading}
                data-testid="upgrade-pro-btn"
              >
                {isLoading ? 'Loading...' : 'Upgrade to Pro'}
              </Button>
            )}
          </motion.div>
        </div>

        {/* FAQ */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-16 text-center"
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
