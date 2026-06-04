## Purpose

Conversational prose voice defines the tone and structure for explanatory web app copy.

## Requirements

### Requirement: Prose uses conversational, emdash-free voice
All explanatory prose in the web app (section blurbs, tooltip footnotes, empty states, About text) SHALL use a conversational tone. Sentences SHALL be short; fragments are permitted where conversationally natural. Emdashes SHALL NOT be used. Contractions (it's, don't, that's) SHALL be preferred over expanded forms (it is, do not, that is).

#### Scenario: No emdashes in any prose
- **WHEN** searching all `.astro` and `.tsx` files for the emdash character (—)
- **THEN** no instance is found outside of the Methodology page

#### Scenario: Fragments appear in blurbs
- **WHEN** reading any section blurb
- **THEN** at least one sentence fragment or very short sentence (under 6 words) is present

#### Scenario: Contractions used where natural
- **WHEN** reading any section blurb
- **THEN** contractions (it's, don't, that's, we're) appear where expanded forms would sound formal

### Requirement: Prose is opinionated, not hedged
Explanatory prose SHALL express a clear point of view. Hedging language (may, might, typically, approximately, nearly always) SHALL be removed unless it conveys a technically meaningful distinction. "Learn more →" links SHALL NOT appear in section blurbs; methodology is accessible from the sidebar.

#### Scenario: No hedging in factual statements
- **WHEN** a blurb describes what a chart shows
- **THEN** it uses direct language ("Shows pass rate per model.") not hedged language ("May show approximate pass rates.")

#### Scenario: No "Learn more" links in blurbs
- **WHEN** searching all `.astro` files for "Learn more"
- **THEN** no instance is found outside of the Methodology page

### Requirement: Prose avoids describing what is already visible
Section blurbs SHALL provide non-obvious context: caveats, insights, or orientation. They SHALL NOT restate chart titles, axis labels, or badge text that the user can see. A chart titled "Token Usage" with a labeled axis does not need a paragraph explaining that it shows token usage.

#### Scenario: Self-explanatory sections have no blurb
- **WHEN** navigating to the Overview page
- **THEN** the "Pass Rate" chart section has no prose blurb above it (the chart title and axes are sufficient)

#### Scenario: Non-obvious context is preserved
- **WHEN** navigating to the Overview page
- **THEN** the "API Time" chart section explains that the metric is API call latency, not full fixture setup or scoring time

### Requirement: One thought per sentence
Each sentence in a blurb SHALL express a single thought. Compound sentences joined by "and" or "while" SHALL be split unless both clauses are under 8 words each.

#### Scenario: Compound sentences are split
- **WHEN** a blurb contains two distinct ideas
- **THEN** they appear as separate sentences or fragments, not joined by a conjunction

### Requirement: Methodology page is exempt
The Methodology page (`/methodology`) is the canonical technical documentation and SHALL NOT be rewritten. It may retain emdashes, formal tone, and "Learn more" links. All other pages SHALL follow the voice guidelines in this specification.

#### Scenario: Methodology page unchanged
- **WHEN** comparing the Methodology page before and after this change
- **THEN** the prose content is identical
