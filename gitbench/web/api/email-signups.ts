import { json } from "../src/lib/report-api.ts";

interface EmailSignupBody {
  email?: unknown;
}

function parseBody(body: unknown): EmailSignupBody | null {
  if (typeof body === "string") {
    try {
      return JSON.parse(body) as EmailSignupBody;
    } catch {
      return null;
    }
  }
  if (body && typeof body === "object") {
    return body as EmailSignupBody;
  }
  return {};
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export default function handler(req: any, res: any) {
  if (req.method !== "POST") {
    res.setHeader("allow", "POST");
    json(res, 405, {
      ok: false,
      error: "method_not_allowed",
    });
    return;
  }

  const body = parseBody(req.body);
  if (!body) {
    json(res, 400, {
      ok: false,
      error: "invalid_json",
    });
    return;
  }

  const email = typeof body.email === "string" ? body.email.trim() : "";
  if (!isValidEmail(email)) {
    json(res, 400, {
      ok: false,
      error: "invalid_email",
    });
    return;
  }

  json(res, 202, {
    ok: true,
    email,
  });
}
