import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  CheckCircle, 
  Cube, 
  Spinner,
  XCircle,
  ArrowRight
} from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
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

const PaymentSuccess = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { checkAuth } = useAuth();
  
  const [status, setStatus] = useState('checking'); // checking, success, failed
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 5;
  const pollInterval = 2000;

  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    if (!sessionId) {
      setStatus('failed');
      return;
    }

    const pollPaymentStatus = async () => {
      try {
        const { data } = await axios.get(`${API}/payments/status/${sessionId}`);
        
        if (data.payment_status === 'paid') {
          setStatus('success');
          // Refresh user data to update isPro status
          await checkAuth();
          return;
        } else if (data.status === 'expired') {
          setStatus('failed');
          return;
        }

        // Continue polling if still pending
        if (attempts < maxAttempts) {
          setAttempts(prev => prev + 1);
          setTimeout(pollPaymentStatus, pollInterval);
        } else {
          setStatus('failed');
        }
      } catch (error) {
        console.error('Payment status check failed:', error);
        if (attempts < maxAttempts) {
          setAttempts(prev => prev + 1);
          setTimeout(pollPaymentStatus, pollInterval);
        } else {
          setStatus('failed');
        }
      }
    };

    pollPaymentStatus();
  }, [sessionId, attempts, checkAuth]);

  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
      <div className="absolute inset-0 grid-pattern opacity-50" />
      
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="neu-surface p-8 rounded-xl text-center max-w-md w-full relative"
      >
        {status === 'checking' && (
          <>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="w-16 h-16 mx-auto mb-6"
            >
              <Spinner size={64} className="text-[var(--primary)]" />
            </motion.div>
            <h1 className="text-2xl font-bold mb-2">Processing Payment</h1>
            <p className="text-[var(--text-secondary)]">
              Please wait while we confirm your payment...
            </p>
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
            <h1 className="text-2xl font-bold mb-2">Payment Successful</h1>
            <p className="text-[var(--text-secondary)] mb-6">
              Your payment was successful. Your account is ready to generate and download the export bundles included with your purchase.
            </p>
            <div className="space-y-3">
              <Button 
                onClick={() => navigate('/designer')}
                className="w-full btn-primary gap-2"
                data-testid="go-to-designer-btn"
              >
                Open Designer <ArrowRight size={18} />
              </Button>
              <Button 
                variant="outline"
                onClick={() => navigate('/library')}
                className="w-full"
                data-testid="go-to-library-btn"
              >
                View Saved Designs
              </Button>
            </div>
          </>
        )}

        {status === 'failed' && (
          <>
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-500 flex items-center justify-center"
            >
              <XCircle size={40} weight="fill" className="text-white" />
            </motion.div>
            <h1 className="text-2xl font-bold mb-2">Payment Issue</h1>
            <p className="text-[var(--text-secondary)] mb-6">
              We couldn't confirm your payment. If you were charged, please contact support and we'll sort it out.
            </p>
            <div className="space-y-3">
              <Button 
                onClick={() => navigate('/pricing')}
                className="w-full btn-primary"
                data-testid="try-again-btn"
              >
                Try Again
              </Button>
              <Button 
                variant="outline"
                onClick={() => navigate('/')}
                className="w-full"
              >
                Back to Home
              </Button>
            </div>
          </>
        )}
      </motion.div>
    </div>
  );
};

export default PaymentSuccess;
