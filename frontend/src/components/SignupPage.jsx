import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2 } from 'lucide-react';
import AuthShell from './AuthShell';
import { FormField } from './FormField';
import authApi from '../api/auth';

export default function SignupPage({ theme, navigate: propNavigate }) {
  const routerNavigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const passwordCriteria = [
    { label: 'At least 10 characters', met: password.length >= 10 },
    { label: 'At least one uppercase letter', met: /[A-Z]/.test(password) },
    { label: 'At least one lowercase letter', met: /[a-z]/.test(password) },
    { label: 'At least one digit (0-9)', met: /\d/.test(password) },
  ];
  const isPasswordValid = passwordCriteria.every((c) => c.met);

  const goToLogin = () => {
    if (typeof propNavigate === 'function') {
      propNavigate('Login');
    }
    routerNavigate('/login');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isPasswordValid) {
      setError('Please satisfy all password requirements before continuing.');
      return;
    }
    setError('');
    setIsSubmitting(true);

    try {
      await authApi.register({
        name: fullName.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        password,
      });
      setSubmitted(true);
      setFullName('');
      setEmail('');
      setPhone('');
      setPassword('');
      setAgreed(false);
    } catch (err) {
      if (err.status === 429) {
        setError('Too many attempts, please try again later');
      } else if (err.status === 422) {
        setError('Please check the entered information and meet all password criteria.');
      } else {
        setError(err.message || 'Something went wrong, please try again');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const footer = (
    <span>
      Already have an account?{' '}
      <button
        type="button"
        onClick={goToLogin}
        className="font-semibold transition-colors focus:outline-none hover:underline"
        style={{ color: theme.green }}
      >
        Log in
      </button>
    </span>
  );

  return (
    <AuthShell
      eyebrow="Sales Representative Registration"
      title={submitted ? "Registration Submitted" : "Join SOLARA Sales Team"}
      subtitle={
        submitted
          ? "Your Sales Representative account has been created successfully."
          : "Create your Sales Representative account to access your CRM leads and authorized pipeline."
      }
      footer={footer}
      theme={theme}
    >
      {submitted ? (
        <div className="py-4 text-center space-y-4">
          <div
            className="w-16 h-16 rounded-full mx-auto flex items-center justify-center"
            style={{ backgroundColor: theme.greenSoft, color: theme.green }}
          >
            <CheckCircle2 className="w-8 h-8" />
          </div>

          <h3 className="text-2xl font-bold tracking-tight" style={{ color: theme.text }}>
            Your account is ready
          </h3>

          <p className="text-sm sm:text-base leading-relaxed max-w-sm mx-auto" style={{ color: theme.textMuted }}>
            You can now log in with the email address and password you just registered.
          </p>

          <button
            type="button"
            onClick={goToLogin}
            className="w-full inline-flex items-center justify-center gap-2.5 font-medium text-base px-6 py-3.5 rounded-full text-white transition-all duration-200 mt-4 focus:outline-none"
            style={{ backgroundColor: theme.green }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = theme.greenHover)}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = theme.green)}
          >
            <span>Proceed to Log In</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <FormField
            label="Full name"
            type="text"
            placeholder="John Doe"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            theme={theme}
          />

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
            label="Phone number"
            type="tel"
            placeholder="(555) 000-0000"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            theme={theme}
          />

          <div className="space-y-2">
            <FormField
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              theme={theme}
            />

            {/* Inline password rules feedback */}
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
                      <span className={criterion.met ? "font-medium" : ""}>{criterion.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Checkbox: I agree to terms */}
          <div className="pt-1">
            <label className="flex items-start gap-2.5 cursor-pointer text-xs sm:text-sm select-none" style={{ color: theme.textMuted }}>
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                required
                className="w-4 h-4 mt-0.5 rounded border cursor-pointer flex-shrink-0"
                style={{ accentColor: theme.green }}
              />
              <span>
                I agree to the{' '}
                <a href="#terms" className="underline font-medium" style={{ color: theme.green }}>
                  Terms of Service
                </a>{' '}
                and{' '}
                <a href="#privacy" className="underline font-medium" style={{ color: theme.green }}>
                  Privacy Policy
                </a>
                .
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={isSubmitting || !agreed || !isPasswordValid}
            className="w-full inline-flex items-center justify-center gap-2.5 font-medium text-base px-6 py-3.5 rounded-full text-white transition-all duration-200 mt-2 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed"
            style={{ backgroundColor: theme.green }}
            onMouseEnter={(e) => {
              if (!isSubmitting && agreed && isPasswordValid) {
                e.currentTarget.style.backgroundColor = theme.greenHover;
              }
            }}
            onMouseLeave={(e) => {
              if (!isSubmitting && agreed && isPasswordValid) {
                e.currentTarget.style.backgroundColor = theme.green;
              }
            }}
          >
            <span>{isSubmitting ? 'Creating account...' : 'Create Account'}</span>
            <ArrowRight className="w-5 h-5" />
          </button>
        </form>
      )}
    </AuthShell>
  );
}
