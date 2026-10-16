import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import AuthShell from './AuthShell';
import { FormField } from './FormField';
import { useAuth } from '../context/AuthContext';

export default function LoginPage({ theme = { bg: '#FBFAF6', card: '#FFFFFF', border: '#D8DED9', text: '#16231C', textMuted: '#4B584F', green: '#1F5C3E', greenHover: '#184A32', input: '#FFFFFF' } }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const session = await login({ email, password, rememberMe });
      if (session?.user?.status && session.user.status !== "Active") {
        throw new Error(`Your account is currently ${session.user.status}. Please contact an administrator or check your activation link.`);
      }
      const redirectPath = location.state?.from?.pathname || '/dashboard';
      navigate(redirectPath, { replace: true });
    } catch (err) {
      setError(err.message || 'Unable to log in. Please check your details and try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const footer = (
    <span>
      Don't have an account?{' '}
      <button
        type="button"
        onClick={() => navigate('/signup')}
        className="font-semibold transition-colors focus:outline-none hover:underline"
        style={{ color: theme.green }}
      >
        Sign up
      </button>
    </span>
  );

  return (
    <AuthShell
      eyebrow="Welcome back"
      title="Log in to your account"
      subtitle="Access your SOLARA dashboard, energy tracking, and customized solar quotes."
      footer={footer}
      theme={theme}
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <FormField
          label="Email address"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          theme={theme}
        />

        <FormField
          label="Password"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          theme={theme}
        />

        {/* Row below fields: Remember me checkbox + Forgot password link */}
        <div className="flex items-center justify-between pt-1">
          <label className="flex items-center gap-2 cursor-pointer text-sm font-medium select-none" style={{ color: theme.textMuted }}>
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded border cursor-pointer"
              style={{ accentColor: theme.green }}
            />
            <span>Remember me</span>
          </label>

          <button
            type="button"
            onClick={() => navigate('/forgot-password')}
            className="text-sm font-medium hover:underline focus:outline-none transition-colors"
            style={{ color: theme.green }}
          >
            Forgot password?
          </button>
        </div>

        {/* Full-width filled green pill Log In button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full inline-flex items-center justify-center gap-2.5 font-medium text-base px-6 py-3.5 rounded-full text-white transition-all duration-200 mt-2 focus:outline-none"
          style={{ backgroundColor: theme.green }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = theme.greenHover)}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = theme.green)}
        >
          <span>{isSubmitting ? 'Logging in...' : 'Log In'}</span>
          <ArrowRight className="w-5 h-5" />
        </button>
      </form>
    </AuthShell>
  );
}
