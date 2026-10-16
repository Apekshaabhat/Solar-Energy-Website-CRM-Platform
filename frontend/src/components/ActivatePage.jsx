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
import authApi from '../api/auth';

export default function ActivatePage({
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
  const [tokenMissing, setTokenMissing] = useState(false);

  useEffect(() => {
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
      window.history.replaceState({}, document.title, window.location.pathname);
    } else {
      setTokenMissing(true);
      setError('Invalid or missing activation token. Please check your invitation email.');
    }
  }, [searchParams]);

  const passwordCriteria = [
    { label: 'At least 10 characters', met: password.length >= 10 },
    { label: 'At least one uppercase letter', met: /[A-Z]/.test(password) },
    { label: 'At least one lowercase letter', met: /[a-z]/.test(password) },
    { label: 'At least one digit (0-9)', met: /\d/.test(password) },
  ];
  const isPasswordValid = passwordCriteria.every((c) => c.met);
  const passwordsMatch = password && password === confirmPassword;

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
    if (tokenMissing || !token) {
      setError('Cannot activate account without a valid invitation token.');
      return;
    }

    if (!isPasswordValid) {
      setError('Please ensure your password satisfies all requirements.');
      return;
    }

    if (!passwordsMatch) {
      setError('Passwords do not match.');
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
      await authApi.activate(token, password);
      navigate('/login', {
        state: { message: 'Account activated successfully. You can now log in.' },
        replace: true,
      });
    } catch (err) {
      if (err.status === 429) {
        setError('Too many attempts, please try again later');
      } else if (err.status === 401 || err.status === 422) {
        setError('Invalid or expired activation link. Please contact your administrator.');
      } else {
        setError('Something went wrong, please try again');
      }
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
      title="Activate your account"
      subtitle="Set your account password to activate your access to SOLARA."
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
              onClick={() => navigate('/login')}
              className="inline-flex items-center justify-center gap-2 font-medium text-sm px-6 py-3 rounded-full text-white transition-colors"
              style={{ backgroundColor: theme.green }}
            >
              Go to Login
            </button>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <FormField
                label="Choose password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                theme={theme}
              />

              {password && (
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
              label="Confirm password"
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
              <span>{isSubmitting ? 'Activating account...' : 'Activate Account'}</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          </>
        )}
      </form>
    </AuthShell>
  );
}
