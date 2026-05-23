## 1. Template changes

- [x] 1.1 Remove `has-tooltip` class from the intro paragraph span and replace `data-tooltip` with `title` attribute
- [x] 1.2 Remove outer `<div class="card p-5">` wrapper from each base model group, keep the `<h3>` model name heading
- [x] 1.3 Replace inner `<div class="card p-3 ...">` chip styling with `bg-neutral-700 rounded-md border border-[#3E3E3E] p-2 transition-colors hover:border-[var(--color-border-accent)] cursor-pointer`
- [x] 1.4 Remove `has-tooltip` and `data-tooltip` from level name span; replace with plain `title` attribute
- [x] 1.5 Remove `has-tooltip` and `data-tooltip` from pass rate badge span
- [x] 1.6 Remove the cost display block (`{l.total_cost_usd != null && (...)}`)
- [x] 1.7 Change provider section spacing from `mb-10` to `mb-6` and inner gap from `gap-4` to `gap-3`

## 2. Verification

- [x] 2.1 Run `npm run build` in `gitbench/web/` to confirm no build errors
- [x] 2.2 Visually verify the Models page renders with compact chips, no outer cards, no info circles, no cost
- [x] 2.3 Verify all level chip links navigate correctly to the model detail pages
- [x] 2.4 Verify mobile layout: chips wrap correctly in the grid at narrow viewport widths
