import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, CheckCircle2 } from 'lucide-react';
import AuthShell from './AuthShell';
import { FormField } from './FormField';
import { authService } from '../services/authService';

export default function ActivatePage({ theme = { bg: '#FBFAF6', card: '#FFFFFF', border: '#D8DED9', text: '#16231C', textMuted: '#4B584F', green: '#1F5C3E', greenHover: '#184A32', input: '#FFFFFF' } }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get('token') || '';

  const [token, setToken] = useState(tokenFromUrl);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (tokenFromUrl) {
      setToken(tokenFromUrl);
    }
  }, [tokenFromUrl]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (!token.trim()) {
      setError('Activation token is required. Please check your invitation link.');
      return;
    }

    setIsSubmitting(true);
    try {
      await authService.activateAccount({
        token: token.trim(),
        password,
        confirmPassword,
      });
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Account activation failed. The token may be expired or invalid.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const footer = (
    <span>
      Already have an active account?{' '}
      <button
        type="button"
        onClick={() => navigate('/login')}
        className="font-semibold transition-colors focus:outline-none hover:underline"
        style={{ color: theme.green }}
      >
        Log in
      </button>
    </span>
  );

  return (
    <AuthShell
      eyebrow="Account Activation"
      title="Set up your password"
      subtitle="Complete your account setup to start using the SOLARA platform."
      footer={footer}
      theme={theme}
    >
      {success ? (
        <div className="space-y-6 text-center py-4">
          <div className="w-16 h-16 bg-emerald-100 text-[#1F5C3E] rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-stone-900">Account Activated Successfully!</h3>
            <p className="text-stone-600 text-sm mt-2">
              Your password has been configured and your account is now active.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="w-full inline-flex items-center justify-center gap-2.5 font-medium text-base px-6 py-3.5 rounded-full text-white transition-all duration-200 focus:outline-none"
            style={{ backgroundColor: theme.green }}
          >
            <span>Proceed to Log In</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {!tokenFromUrl && (
            <FormField
              label="Activation Token"
              type="text"
              placeholder="Paste invitation token here"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
              theme={theme}
            />
          )}

          <FormField
            label="Create Password"
            type="password"
            placeholder="Minimum 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            theme={theme}
          />

          <FormField
            label="Confirm Password"
            type="password"
            placeholder="Re-enter your password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            theme={theme}
          />

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full inline-flex items-center justify-center gap-2.5 font-medium text-base px-6 py-3.5 rounded-full text-white transition-all duration-200 mt-2 focus:outline-none"
            style={{ backgroundColor: theme.green }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = theme.greenHover)}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = theme.green)}
          >
            <span>{isSubmitting ? 'Activating Account...' : 'Activate & Set Password'}</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </form>
      )}
    </AuthShell>
  );
}
