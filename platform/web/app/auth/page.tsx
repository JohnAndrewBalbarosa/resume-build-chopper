"use client";

import { FormEvent, useMemo, useState } from "react";
import { LogIn, Network, ShieldCheck } from "lucide-react";
import { ParticleField } from "@/components/particle-field";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { isSchoolEmail } from "@/lib/permissions";

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [access, setAccess] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const emailValid = useMemo(() => email.length === 0 || isSchoolEmail(email), [email]);
  const accessValid = access.length === 0 || access.trim().length >= 6;
  const canSubmit = isSchoolEmail(email) && access.trim().length >= 6;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <main className="grid min-h-screen bg-canvas text-ink lg:grid-cols-[1.1fr_0.9fr]">
      <section className="relative hidden overflow-hidden bg-[#0B0B0C] lg:block">
        <ParticleField density={118} />
        <div className="relative z-10 flex h-full items-end p-10 text-white">
          <div className="max-w-xl">
            <Badge variant="orange">
              <Network size={14} />
              Secure campus node
            </Badge>
            <h1 className="mt-5 text-5xl font-extrabold tracking-[-0.02em]">Campus intelligence starts at trusted identity.</h1>
            <p className="mt-5 leading-7 text-[#B6C2D1]">
              Official school accounts become the first boundary before Supabase Auth, RLS, and role-aware dashboards.
            </p>
          </div>
        </div>
      </section>

      <section className="flex items-center justify-center px-4 py-10 sm:px-6">
        <Card className="w-full max-w-md bg-surface">
          <div className="mb-6">
            <Badge variant="orange">
              <ShieldCheck size={14} />
              FEU Tech access
            </Badge>
            <h2 className="mt-4 text-2xl font-bold tracking-[-0.02em]">Sign in or request access</h2>
            <p className="mt-2 text-sm leading-6 text-muted">Use an official `@feutech.edu.ph` or `@fit.edu.ph` address.</p>
          </div>
          <form className="space-y-4" onSubmit={submit}>
            <div>
              <Label htmlFor="email">School email</Label>
              <Input
                aria-invalid={!emailValid}
                autoComplete="email"
                id="email"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="student@feutech.edu.ph"
                type="email"
                value={email}
              />
              {!emailValid && <p className="mt-2 text-sm text-danger">Only @feutech.edu.ph or @fit.edu.ph accounts can register.</p>}
            </div>
            <div>
              <Label htmlFor="access">Access code</Label>
              <Input
                aria-invalid={!accessValid}
                id="access"
                onChange={(event) => setAccess(event.target.value)}
                placeholder="AI-STUDY-2026"
                type="text"
                value={access}
              />
              {!accessValid && <p className="mt-2 text-sm text-danger">Access code must be at least 6 characters.</p>}
            </div>
            <Button className="w-full" disabled={!canSubmit} type="submit">
              <LogIn size={18} />
              Continue
            </Button>
            {submitted && canSubmit && (
              <p className="rounded-lg border border-success/30 bg-success/10 p-3 text-sm text-success">
                Prototype validation passed. Supabase Auth handoff belongs in the next integration phase.
              </p>
            )}
          </form>
        </Card>
      </section>
    </main>
  );
}
