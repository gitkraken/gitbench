import * as React from "react";
import { ArrowRight, FileText, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const PRIVACY_URL = "https://www.gitkraken.com/privacy";

export default function EmailCta() {
  const [email, setEmail] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [submittedEmail, setSubmittedEmail] = React.useState<string | null>(
    null,
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;

    if (!form.reportValidity()) {
      return;
    }

    const trimmedEmail = email.trim();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/email-signups", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({ email: trimmedEmail }),
      });
      const body = await response.json();

      if (!response.ok || !body.ok) {
        throw new Error(body.error ?? "signup_failed");
      }

      setSubmittedEmail(body.email ?? trimmedEmail);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog
      onOpenChange={(open) => {
        if (!open) {
          setSubmittedEmail(null);
          setError(null);
          setIsSubmitting(false);
          setEmail("");
        }
      }}
    >
      <div className="relative isolate overflow-hidden rounded-[8px] border border-[#01FEE0]/35 bg-[linear-gradient(135deg,rgba(39,39,39,0.98)_0%,rgba(42,23,61,0.96)_58%,rgba(1,183,161,0.16)_100%)] p-5 shadow-[0_18px_50px_rgba(0,0,0,0.34),0_0_0_1px_rgba(236,127,255,0.08)] sm:p-6">
        <div className="pointer-events-none absolute inset-y-0 right-0 z-0 w-1/2 bg-[linear-gradient(90deg,transparent_0%,rgba(1,254,224,0.08)_100%)]" />
        <Mail
          aria-hidden="true"
          className="pointer-events-none absolute -right-10 -bottom-14 z-0 size-44 rotate-[-12deg] text-[#01FEE0]/[0.12] sm:-right-6 sm:-bottom-20 sm:size-64 md:-right-2 md:-bottom-24 md:size-72"
        />
        <div className="relative z-10 grid gap-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center md:gap-6">
          <div className="flex min-w-0 gap-4">
            {/* <div className="flex size-11 shrink-0 items-center justify-center rounded-[8px] border border-[#01FEE0]/35 bg-[#01FEE0]/10 text-[#01FEE0] shadow-[0_0_22px_rgba(1,254,224,0.12)]">
              <FileText aria-hidden="true" className="size-5" />
            </div> */}
            <div className="min-w-0">
              <div className="section-label mb-3">
                <span>Analysis PDF</span>
              </div>
              <h2 className="mb-2 text-xl font-bold leading-tight text-(--color-text)">
                Get the GitBench analysis PDF
              </h2>
              <p className="max-w-2xl text-sm leading-relaxed text-(--color-text-mid)">
                Request the GitBench analysis PDF and we&apos;ll follow up by
                email with our read on the benchmark results.
              </p>
            </div>
          </div>
        </div>

        <DialogTrigger asChild>
          <Button className="w-full md:w-auto mt-4">
            Get the analysis PDF
            <ArrowRight aria-hidden="true" className="size-4" />
          </Button>
        </DialogTrigger>
      </div>

      <DialogContent className="border-(--color-border) bg-(--color-bg) text-(--color-text) sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Request the GitBench analysis PDF</DialogTitle>
          <DialogDescription className="text-(--color-text-mid)">
            Enter your email and we&apos;ll send the GitBench analysis PDF with
            our notes on the benchmark results.
          </DialogDescription>
        </DialogHeader>

        {submittedEmail ? (
          <div
            className="rounded-[8px] border border-(--color-pass-border) bg-(--color-pass-bg) p-4"
            role="status"
          >
            <p className="text-sm font-semibold text-(--color-text)">
              Thanks. We received {submittedEmail} and will follow up with the
              analysis PDF.
            </p>
          </div>
        ) : (
          <form className="grid gap-4" onSubmit={handleSubmit}>
            <label className="grid gap-2 text-sm font-semibold text-(--color-text)">
              Email
              <input
                className="h-11 rounded-[5px] border-2 border-(--color-border) bg-(--color-surface) px-3 text-sm font-medium text-(--color-text) outline-none transition-colors placeholder:text-(--color-text-dim) hover:border-(--color-border-accent) focus:border-(--color-accent) focus:ring-2 focus:ring-(--color-accent-glow)"
                name="email"
                type="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setError(null);
                }}
                placeholder="you@example.com"
                autoComplete="email"
                disabled={isSubmitting}
                required
              />
            </label>
            {error && (
              <p
                className="text-sm font-semibold text-(--color-fail)"
                role="alert"
              >
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Submitting..." : "Request PDF"}
              <ArrowRight aria-hidden="true" className="size-4" />
            </Button>
          </form>
        )}

        <p className="border-t border-(--color-border) pt-4 text-xs leading-relaxed text-(--color-text-dim)">
          We respect your{" "}
          <a
            className="font-semibold text-(--color-accent) underline-offset-4 hover:text-[#C170FF] hover:underline"
            href={PRIVACY_URL}
            target="_blank"
            rel="noreferrer noopener"
          >
            privacy
          </a>{" "}
          and will never share your information.
        </p>
      </DialogContent>
    </Dialog>
  );
}
