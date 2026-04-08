import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Mail, Loader2, CheckCircle2 } from 'lucide-react';
import api from '@/lib/api';
import toast from 'react-hot-toast';

export default function VerifyEmail() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const email = params.get('email') || '';
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  useEffect(() => {
    if (resendCooldown > 0) {
      const t = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [resendCooldown]);

  const handleChange = (index: number, value: string) => {
    if (value.length > 1) value = value[0];
    if (!/^\d*$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    if (value && index < 5) {
      const next = document.getElementById(`otp-${index + 1}`);
      next?.focus();
    }
    if (newOtp.every(d => d) && newOtp.join('').length === 6) {
      handleVerify(newOtp.join(''));
    }
  };

  const handleVerify = async (code?: string) => {
    const otpStr = code || otp.join('');
    if (otpStr.length !== 6) { toast.error('Enter 6-digit code'); return; }
    setLoading(true);
    try {
      await api.post('/auth/verify-email', { email, otp: otpStr });
      toast.success('Email verified! Please sign in.');
      navigate('/login');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    try {
      await api.post('/auth/resend-otp', { email });
      toast.success('New code sent!');
      setResendCooldown(60);
    } catch {
      toast.error('Failed to resend');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-xl border shadow-sm p-8 space-y-6 text-center">
        <div className="h-14 w-14 rounded-2xl bg-blue-50 flex items-center justify-center mx-auto">
          <Mail className="h-7 w-7 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Verify Your Email</h1>
          <p className="text-sm text-gray-500 mt-2">We sent a 6-digit code to <strong className="text-gray-700">{email}</strong></p>
        </div>
        <div className="flex justify-center gap-2">
          {otp.map((digit, i) => (
            <input key={i} id={`otp-${i}`} type="text" inputMode="numeric" maxLength={1} value={digit}
              onChange={e => handleChange(i, e.target.value)}
              onKeyDown={e => { if (e.key === 'Backspace' && !digit && i > 0) document.getElementById(`otp-${i-1}`)?.focus(); }}
              className="w-11 h-13 text-center text-xl font-bold border-2 border-gray-200 rounded-lg focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none" />
          ))}
        </div>
        <button onClick={() => handleVerify()} disabled={loading || otp.join('').length < 6}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-primary text-white font-medium text-sm disabled:opacity-50">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
          {loading ? 'Verifying...' : 'Verify Email'}
        </button>
        <p className="text-sm text-gray-500">
          Didn't receive the code?{' '}
          {resendCooldown > 0 ? (
            <span className="text-gray-400">Resend in {resendCooldown}s</span>
          ) : (
            <button onClick={handleResend} className="text-accent font-medium hover:underline">Resend</button>
          )}
        </p>
      </div>
    </div>
  );
}