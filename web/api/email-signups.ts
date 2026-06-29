import { json } from "../src/lib/report-api.ts";

const HUBSPOT_PORTAL_ID = "544893";
const HUBSPOT_FORM_ID = "22143c4c-3889-47a0-9ffa-b22deb639ba7";
const HUBSPOT_SUBMISSION_ERROR =
  "We could not submit your email right now. Please try again shortly.";

interface EmailSignupBody {
  email?: unknown;
}

type HubSpotField = {
  name: string;
  value: string;
};

type HubSpotPayload = {
  fields: HubSpotField[];
};

export function buildHubSpotPayload(data: { email: string }): HubSpotPayload {
  return {
    fields: [{ name: "0-1/email", value: data.email }],
  };
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

export default async function handler(req: any, res: any) {
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
      error: "Please enter a valid email address.",
    });
    return;
  }

  const hubSpotUrl = `https://api.hsforms.com/submissions/v3/integration/submit/${HUBSPOT_PORTAL_ID}/${HUBSPOT_FORM_ID}`;

  try {
    const response = await fetch(hubSpotUrl, {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(buildHubSpotPayload({ email })),
    });

    if (!response.ok) {
      console.error("HubSpot email signup submission failed", {
        status: response.status,
        statusText: response.statusText,
      });

      json(res, 502, {
        ok: false,
        error: HUBSPOT_SUBMISSION_ERROR,
      });
      return;
    }
  } catch (error) {
    console.error("HubSpot email signup request failed", error);
    json(res, 502, {
      ok: false,
      error: HUBSPOT_SUBMISSION_ERROR,
    });
    return;
  }

  json(res, 200, {
    ok: true,
    email,
  });
}
