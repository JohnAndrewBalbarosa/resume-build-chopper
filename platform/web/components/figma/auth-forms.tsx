"use client";

import type { ComponentType, InputHTMLAttributes } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowRight, CheckCircle2, Lock, Mail, User as UserIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { AuthShell } from "./auth-shell";
import { isSchoolEmail } from "@/lib/permissions";

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  icon: ComponentType<{ size?: number; className?: string }>;
};

function Field({ icon: Icon, className: _className, ...props }: FieldProps) {
  return (
    <div className="relative">
      <Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#FFF7ED]/30" size={16} />
      <input
        className="focus-ring w-full rounded-lg border border-white/10 bg-white/[0.04] py-3 pl-10 pr-4 text-[#FFF7ED] placeholder:text-[#FFF7ED]/30 transition-all duration-300 focus:border-[#e8590c]/50 focus:bg-white/[0.06]"
        {...props}
      />
    </div>
  );
}

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const emailValid = useMemo(() => email.length === 0 || isSchoolEmail(email), [email]);
  const canSubmit = isSchoolEmail(email) && password.length >= 8;

  return (
    <AuthShell sub="// sign in" title="Welcome back, builder.">
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (canSubmit) router.push("/dashboard");
        }}
      >
        <Field
          aria-invalid={!emailValid}
          autoComplete="email"
          icon={Mail}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@fit.edu.ph"
          required
          type="email"
          value={email}
        />
        {!emailValid && <p className="text-xs text-[#e8590c]">Use @fit.edu.ph or @feutech.edu.ph.</p>}
        <Field
          autoComplete="current-password"
          icon={Lock}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          required
          type="password"
          value={password}
        />
        <div className="flex items-center justify-between text-sm">
          <label className="flex items-center gap-2 text-[#FFF7ED]/60">
            <input className="accent-[#e8590c]" type="checkbox" />
            Remember device
          </label>
          <a className="text-[#e8590c] hover:underline" href="#">Forgot?</a>
        </div>
        <button
          className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#e8590c] to-[#ff7a2d] py-3 text-white shadow-lg shadow-[#e8590c]/30 transition-all duration-300 hover:shadow-[#e8590c]/50 disabled:cursor-not-allowed disabled:opacity-55"
          disabled={!canSubmit}
          type="submit"
        >
          Sign in <ArrowRight size={15} />
        </button>
      </form>
      <div className="mt-8 text-center text-sm text-[#FFF7ED]/50">
        New to the chapter? <Link className="text-[#e8590c] hover:underline" href="/register">Register</Link>
      </div>
    </AuthShell>
  );
}

export function RegisterForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const emailValid = isSchoolEmail(email);
  const passwordValid = password.length >= 8;
  const confirmValid = confirm.length === 0 || confirm === password;
  const canSubmit = emailValid && passwordValid && confirm === password;

  return (
    <AuthShell sub="// create account" title="Join PyTorch.FIT.">
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (!emailValid) {
            setError("Registration requires @fit.edu.ph or @feutech.edu.ph.");
            return;
          }
          if (!passwordValid || confirm !== password) {
            setError("Password must be 8+ characters and match confirmation.");
            return;
          }
          router.push("/dashboard");
        }}
      >
        <Field autoComplete="name" icon={UserIcon} placeholder="Full name" required />
        <Field
          aria-invalid={email.length > 0 && !emailValid}
          autoComplete="email"
          icon={Mail}
          onChange={(event) => {
            setEmail(event.target.value);
            setError("");
          }}
          placeholder="you@fit.edu.ph"
          required
          type="email"
          value={email}
        />
        {email && (
          <div className={`flex items-center gap-2 font-mono text-xs ${emailValid ? "text-green-400" : "text-[#e8590c]"}`}>
            {emailValid ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
            {emailValid ? "School email verified" : "Must be @fit.edu.ph or @feutech.edu.ph"}
          </div>
        )}
        <Field
          autoComplete="new-password"
          icon={Lock}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          required
          type="password"
          value={password}
        />
        <Field
          aria-invalid={!confirmValid}
          autoComplete="new-password"
          icon={Lock}
          onChange={(event) => setConfirm(event.target.value)}
          placeholder="Confirm password"
          required
          type="password"
          value={confirm}
        />
        {!confirmValid && <p className="text-xs text-[#e8590c]">Passwords must match.</p>}
        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-[#e8590c]/30 bg-[#e8590c]/10 p-3 text-xs text-[#e8590c]">
            <AlertCircle className="mt-0.5 flex-none" size={14} />
            {error}
          </div>
        )}
        <label className="flex items-start gap-2 text-xs leading-5 text-[#FFF7ED]/50">
          <input className="mt-0.5 accent-[#e8590c]" required type="checkbox" />
          I agree to FEU Tech community guidelines and consent to role-based visibility gates in this prototype.
        </label>
        <button
          className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#e8590c] to-[#ff7a2d] py-3 text-white shadow-lg shadow-[#e8590c]/30 transition-all duration-300 hover:shadow-[#e8590c]/50 disabled:cursor-not-allowed disabled:opacity-55"
          disabled={!canSubmit}
          type="submit"
        >
          Create account <ArrowRight size={15} />
        </button>
      </form>
      <div className="mt-8 text-center text-sm text-[#FFF7ED]/50">
        Already a member? <Link className="text-[#e8590c] hover:underline" href="/login">Sign in</Link>
      </div>
    </AuthShell>
  );
}
