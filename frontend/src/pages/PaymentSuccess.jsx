import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  CheckCircle,
  Cube,
  Spinner,
  XCircle,
  ArrowRight,
  ClockCounterClockwise,
} from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
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

const PaymentSuccess = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { checkAuth } = useAuth();

  const [status, setStatus] = useState('checking'); // checking, success, pending, failed
  const [attempts, setAttempts] = useState(0);
  const [lastMessage, setLastMessage] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const sessionId = searchParams.get('session_id');
  const checkoutType = searchParams.get('type') || 'single';

  const maxAttempts = 12;
  const pollInterval = 2500;

  const checkPaymentStatus = useCallback(async () => {
    if (!sessionId) {
      setStatus('failed');
      setLastMessage('No checkout session was supplied.');
      return;
    }

    setIsRefreshing(true);

    try {
      const { data } = await axios.get(`${API}/payments/status/${sessionId}`);

      if (data.payment_status === 'paid' || data.status === 'complete') {
        setStatus('success');
        setLastMessage('Payment confirmed.');
        await checkAuth();
        return;
      }

      if (data.status === 'expired' || data.payment_status === 'failed') {
        setStatus('failed');
        setLastMessage('Payment could not be confirmed.');
        return;
      }

      setStatus('pending');
      setLastMessage(data.message || 'Payment confirmation is still pending.');
    } catch (error) {
      setStatus('pending');
      setLastMessage('Payment confirmation is still pending. This can take a short time after checkout.');
    } finally {
      setIsRefreshing(false);
    }
  }, [sessionId, checkAuth]);

  useEffect(() => {
    if (!sessionId) {
      setStatus('failed');
      setLastMessage('No checkout session was supplied.');
      return;
    }

    let timer;

    const poll = async () => {
      await checkPaymentStatus();

      setAttempts((prev) => {
        const next = prev + 1;
        if (next < maxAttempts) {
          timer = setTimeout(poll, pollInterval);
        }
        return next;
      });
    };

    poll();

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [sessionId, checkPaymentStatus]);

  const isSingleExport = checkoutType === 'single';

  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
      <div className="absolute inset-0 grid-pattern opacity-50" />

      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative neu-surface p-8 rounded-2xl max-w-md w-full text-center"
        data-testid="payment-success-page"
      >
        <div className="flex items-center justify-center gap-2 mb-6">
          <Cube size={28} className="text-[var(--primary)]" />
          <span className="font-bold">UltimateDesk</span>
        </div>

        {status === 'checking' && (
          <>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="w-16 h-16 mx-auto mb-6"
            >
              <Spinner size={64} className="text-[var(--primary)]" />
            </motion.div>
            <h1 className="text-2xl font-bold mb-2">Confirming Payment</h1>
            <p className="text-[var(--text-secondary)]">
              Please wait while we confirm your checkout session.
            </p>
          </>
        )}

        {status === 'pending' && (
          <>
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-yellow-500/20 flex items-center justify-center">
              <ClockCounterClockwise size={40} weight="fill" className="text-yellow-500" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Payment Confirmation Pending</h1>
            <p className="text-[var(--text-secondary)] mb-3">
              Your checkout page has returned, but payment confirmation is still pending.
              This is normal if the payment webhook is still processing.
            </p>
            <p className="text-xs text-[var(--text-secondary)] mb-6">
              {lastMessage || 'We will keep checking for a short time.'}
            </p>

            <div className="space-y-3">
              <Button
                onClick={checkPaymentStatus}
                disabled={isRefreshing}
                className="w-full btn-primary"
                data-testid="refresh-payment-status-btn"
              >
                {isRefreshing ? 'Checking...' : 'Check Again'}
              </Button>

              <Button
                variant="outline"
                onClick={() => navigate(isSingleExport ? '/designer' : '/pricing')}
                className="w-full"
                data-testid="continue-after-pending-btn"
              >
                {isSingleExport ? 'Back to Designer' : 'Back to Pricing'}
              </Button>
            </div>
          </>
        )}

        {status === 'success' && (
          <>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 200 }}
              className="w-16 h-16 mx-auto mb-6 rounded-full bg-[var(--success)] flex items-center justify-center"
            >
              <CheckCircle size={40} weight="fill" className="text-white" />
            </motion.div>

            <h1 className="text-2xl font-bold mb-2">Payment Confirmed</h1>
            <p className="text-[var(--text-secondary)] mb-6">
              {isSingleExport
                ? 'Your export credit is ready. Return to the designer and generate your files.'
                : 'Your Pro access is ready. You can now generate export bundles while subscribed.'}
            </p>

            <div className="space-y-3">
              <Button
                onClick={() => navigate('/designer')}
                className="w-full btn-primary"
                data-testid="go-to-designer-btn"
              >
                {isSingleExport ? 'Generate Export Files' : 'Open Designer'}
                <ArrowRight size={18} className="ml-2" />
              </Button>

              <Button
                variant="outline"
                onClick={() => navigate('/library')}
                className="w-full"
                data-testid="go-to-library-btn"
              >
                My Designs
              </Button>
            </div>
          </>
        )}

        {status === 'failed' && (
          <>
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-500 flex items-center justify-center">
              <XCircle size={40} weight="fill" className="text-white" />
            </div>

            <h1 className="text-2xl font-bold mb-2">Payment Could Not Be Confirmed</h1>
            <p className="text-[var(--text-secondary)] mb-3">
              We could not confirm this checkout session.
            </p>
            <p className="text-xs text-[var(--text-secondary)] mb-6">
              {lastMessage || 'If you were charged, contact support and we will sort it out.'}
            </p>

            <div className="space-y-3">
              <Button
                onClick={checkPaymentStatus}
                disabled={isRefreshing}
                className="w-full btn-primary"
                data-testid="retry-payment-status-btn"
              >
                {isRefreshing ? 'Checking...' : 'Check Again'}
              </Button>

              <Button
                variant="outline"
                onClick={() => navigate('/pricing')}
                className="w-full"
                data-testid="try-again-btn"
              >
                Back to Pricing
              </Button>

              <Button
                variant="ghost"
                onClick={() => navigate('/')}
                className="w-full"
                data-testid="back-home-btn"
              >
                Back to Home
              </Button>
            </div>
          </>
        )}

        <div className="mt-6 pt-4 border-t border-[var(--border)] text-xs text-[var(--text-secondary)]">
          Session: {sessionId ? `${sessionId.slice(0, 10)}...` : 'missing'}
        </div>
      </motion.div>
    </div>
  );
};

export default PaymentSuccess;
