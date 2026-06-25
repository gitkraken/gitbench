import * as React from "react";
import { ArrowRight, Mail } from "lucide-react";

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
    null
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
          : "Something went wrong. Please try again."
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
      <div className="card grid gap-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
        <div className="flex min-w-0 gap-4">
          <div className="flex size-11 shrink-0 items-center justify-center rounded-[8px] border border-(--color-border) bg-white/[0.04] text-(--color-accent)">
            <Mail aria-hidden="true" className="size-5" />
          </div>
          <div className="min-w-0">
            <div className="section-label mb-3">
              <span>Updates</span>
            </div>
            <h2 className="mb-2 text-xl font-bold leading-tight text-(--color-text)">
              Get GitBench updates in your inbox
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-(--color-text-mid)">
              Leave an email and we will send new model runs, benchmark changes,
              and release notes when they matter.
            </p>
          </div>
        </div>
        <DialogTrigger asChild>
          <Button className="w-full md:w-auto">
            Join the list
            <ArrowRight aria-hidden="true" className="size-4" />
          </Button>
        </DialogTrigger>
      </div>

      <DialogContent className="border-(--color-border) bg-(--color-bg) text-(--color-text) sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Get GitBench updates</DialogTitle>
          <DialogDescription className="text-(--color-text-mid)">
            Enter your email to receive benchmark updates and model result notes.
          </DialogDescription>
        </DialogHeader>

        {submittedEmail ? (
          <div
            className="rounded-[8px] border border-(--color-pass-border) bg-(--color-pass-bg) p-4"
            role="status"
          >
            <p className="text-sm font-semibold text-(--color-text)">
              Thanks. We received {submittedEmail}.
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
              {isSubmitting ? "Submitting..." : "Submit"}
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
