import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, Lock, CheckCircle2 } from 'lucide-react';
import AuthShell from './AuthShell';
import { FormField } from './FormField';
import authApi from '../api/auth';

export default function ResetPasswordPage({
  theme = {
    bg: '#FBFAF6',
    card: '#FFFFFF',
    border: '#D8DED9',
    text: '#16231C',
    textMuted: '#4B584F',
    green: '#1F5C3E',
    greenHover: '#184A32',
    input: '#FFFFFF',
  },
}) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [tokenMissing, setTokenMissing] = useState(false);

  useEffect(() => {
    // Read token from search params or hash search params
    let extractedToken = searchParams.get('token');
    if (!extractedToken && window.location.hash.includes('token=')) {
      const hashQuery = window.location.hash.split('?')[1];
      if (hashQuery) {
        const params = new URLSearchParams(hashQuery);
        extractedToken = params.get('token');
      }
    }

    if (extractedToken) {
      setToken(extractedToken);
      // Remove token from browser URL without reloading
      window.history.replaceState({}, document.title, window.location.pathname);
    } else {
      setTokenMissing(true);
      setError('Invalid or missing password reset token. Please request a new link.');
    }
  }, [searchParams]);

  const passwordCriteria = [
    { label: 'At least 10 characters', met: newPassword.length >= 10 },
    { label: 'At least one uppercase letter', met: /[A-Z]/.test(newPassword) },
    { label: 'At least one lowercase letter', met: /[a-z]/.test(newPassword) },
    { label: 'At least one digit (0-9)', met: /\d/.test(newPassword) },
  ];
  const isPasswordValid = passwordCriteria.every((c) => c.met);
  const passwordsMatch = newPassword && newPassword === confirmPassword;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (tokenMissing || !token) {
      setError('Cannot reset password without a valid token. Please request a new reset link.');
      return;
    }

    if (!isPasswordValid) {
      setError('Please ensure your new password satisfies all requirements.');
      return;
    }

    if (!passwordsMatch) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await authApi.resetPassword(token, newPassword);
      navigate('/login', {
        state: { message: 'Password reset successfully. Please log in with your new password.' },
        replace: true,
      });
    } catch (err) {
      if (err.status === 429) {
        setError('Too many attempts, please try again later');
      } else if (err.status === 401 || err.status === 422) {
        setError('Invalid or expired reset link. Please request a new password reset.');
      } else {
        setError('Something went wrong, please try again');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const footer = (
    <span>
      Remember your password?{' '}
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
      eyebrow="Security"
      title="Reset your password"
      subtitle="Enter a new secure password for your SOLARA account."
      footer={footer}
      theme={theme}
    >
      <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {tokenMissing ? (
          <div className="text-center py-4">
            <button
              type="button"
              onClick={() => navigate('/forgot-password')}
              className="inline-flex items-center justify-center gap-2 font-medium text-sm px-6 py-3 rounded-full text-white transition-colors"
              style={{ backgroundColor: theme.green }}
            >
              Request New Reset Link
            </button>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <FormField
                label="New password"
                type="password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                theme={theme}
              />

              {newPassword && (
                <div className="rounded-xl p-3 bg-gray-50/70 dark:bg-white/5 border border-gray-100 dark:border-white/10 space-y-1.5 mt-2">
                  <p className="text-xs font-semibold" style={{ color: theme.textMuted }}>
                    Password requirements:
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
                    {passwordCriteria.map((criterion, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-1.5"
                        style={{ color: criterion.met ? theme.green : theme.textMuted }}
                      >
                        <span
                          className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                            criterion.met
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                              : "bg-gray-200 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                          }`}
                        >
                          {criterion.met ? "✓" : "•"}
                        </span>
                        <span className={criterion.met ? "font-medium" : ""}>
                          {criterion.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <FormField
              label="Confirm new password"
              type="password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              theme={theme}
            />

            {confirmPassword && !passwordsMatch && (
              <p className="text-xs text-red-600 font-medium">Passwords do not match.</p>
            )}

            <button
              type="submit"
              disabled={isSubmitting || !isPasswordValid || !passwordsMatch}
              className="w-full inline-flex items-center justify-center gap-2.5 font-medium text-base px-6 py-3.5 rounded-full text-white transition-all duration-200 mt-2 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ backgroundColor: theme.green }}
              onMouseEnter={(e) => {
                if (!isSubmitting && isPasswordValid && passwordsMatch) {
                  e.currentTarget.style.backgroundColor = theme.greenHover;
                }
              }}
              onMouseLeave={(e) => {
                if (!isSubmitting && isPasswordValid && passwordsMatch) {
                  e.currentTarget.style.backgroundColor = theme.green;
                }
              }}
            >
              <span>{isSubmitting ? 'Resetting password...' : 'Update Password'}</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          </>
        )}
      </form>
    </AuthShell>
  );
}
