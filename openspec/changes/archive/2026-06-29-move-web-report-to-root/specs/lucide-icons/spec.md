## MODIFIED Requirements

### Requirement: lucide-react is a project dependency
The `lucide-react` package SHALL be added to `web/package.json` as a production dependency.

#### Scenario: Build succeeds with lucide-react
- **WHEN** `npm run build` or `pnpm build` is executed from `web/`
- **THEN** the Astro build completes without errors related to Lucide imports

#### Scenario: No client JS for sidebar icons
- **WHEN** the page loads in a browser
- **THEN** no React or Lucide JavaScript is loaded for sidebar icons (they render server-side as static SVGs)
