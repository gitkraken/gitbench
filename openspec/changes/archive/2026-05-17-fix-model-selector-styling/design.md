## Context

The `ModelSelector` component wraps shadcn/ui's `MultiSelect`, which in turn uses `cmdk`'s `Command` primitives. Currently the "Select all" / "Clear" action buttons live inside `<CommandGroup>` within `<CommandList>` — the scrollable region. The pass-rate badges use colored text classes (`text-[var(--color-pass)]`, etc.) that become illegible against the `bg-accent` (`#06b6d4` cyan) applied on `data-[selected=true]`.

## Goals / Non-Goals

**Goals:**
- Keep "Select all" and "Clear" buttons visible at the top of the dropdown regardless of scroll position
- Make pass-rate percentage badges readable when the option row is hovered or selected (keyboard + mouse)
- Preserve existing behavior and keyboard accessibility

**Non-Goals:**
- Redesigning the badge component or color system
- Changing the dropdown's overall layout structure
- Modifying any other chart component

## Decisions

### 1. Sticky buttons: Move buttons above `<CommandList>`, keep separator below

**Decision:** Extract the action buttons from inside `<CommandGroup>`/`<CommandList>` into a new wrapper between `<CommandInput>` and `<CommandList>`. Add a bottom border separator (via the existing `CommandSeparator`) below the buttons instead of separating them from the list items.

**Rationale:** The `Command` component is `flex flex-col overflow-hidden`. `CommandInput` and `CommandList` (with `overflow-y-auto`) are siblings. Placing the buttons as another sibling between them, outside the scrollable `CommandList`, naturally keeps them fixed. The separator provides visual separation from the scrollable items below.

**Alternative considered:** CSS `position: sticky` on the button row inside `CommandList`. Rejected because it fights the `cmdk` virtual list behavior and adds unnecessary complexity.

### 2. Pass-rate badges on hover/select: Use solid background badges instead of outline

**Decision:** Change the pass-rate `Badge` from `variant="outline"` to a filled variant that uses the pass/warn/fail background colors (`--color-pass-bg`, etc.) with matching text. On hover/selection, the solid badge's internal contrast remains readable regardless of the row background.

**Rationale:** The current `variant="outline"` badge is mostly transparent, so the text color competes directly with the row's `bg-accent`. A filled badge with its own opaque background (e.g., `bg-[var(--color-pass-bg)] text-[var(--color-pass)]`) maintains legibility whether the row is in default, hover, or selected state.

**Alternative considered:** Conditionally swap text color to white/high-contrast on `data-[selected=true]`. Rejected because it requires tracking hover state in React (adding complexity) and doesn't address the hover (but-not-selected) state elegantly. The filled badge approach is simpler and always readable.

### 3. No new props or API surface changes

**Decision:** Both changes are internal to `MultiSelect` and `ModelSelector`. No props, callbacks, or exported types change.

## Risks / Trade-offs

- **Filled badges may look slightly different from existing outline badges** → Mitigation: The filled look is more readable and consistent with badge usage elsewhere in the app (e.g., selected-model badges in the trigger area). The visual change is net positive.
- **Moving buttons out of CommandGroup changes keyboard navigation order** → Mitigation: The buttons are mouse-targeted controls; keyboard users can use Ctrl+A / Escape equivalents if supported by cmdk. The keyboard navigation of the list (arrow keys) is unaffected because the buttons sit above, not inside, the list.
