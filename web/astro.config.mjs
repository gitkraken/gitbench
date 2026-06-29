// @ts-check
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

import react from "@astrojs/react";

const vercelUrl =
  process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL;
const site =
  process.env.PUBLIC_SITE_URL ||
  (vercelUrl ? `https://${vercelUrl}` : undefined);

// https://astro.build/config
export default defineConfig({
  site,
  output: "static",
  integrations: [react()],
  vite: {
    plugins: [tailwindcss()],
    server: {
      allowedHosts: ["gitbench.ngrok.app"],
    },
  },
});
