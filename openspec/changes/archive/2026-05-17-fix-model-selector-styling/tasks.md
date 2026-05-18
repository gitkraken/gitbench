## 1. Sticky quick-select buttons

- [x] 1.1 Move "Select all" / "Clear" buttons from inside `<CommandGroup>` / `<CommandList>` to a new container between `<CommandInput>` and `<CommandList>` in `multi-select.tsx`
- [x] 1.2 Add a `CommandSeparator` below the buttons to visually separate the sticky header from the scrollable list
- [x] 1.3 Verify the buttons remain visible at the top when scrolling the dropdown on the Compare page

## 2. Pass-rate badge readability

- [x] 2.1 Change pass-rate `Badge` in `ModelSelector.tsx` from `variant="outline"` to a filled variant using `bg-[var(--color-pass-bg)]`, `bg-[var(--color-warn-bg)]`, `bg-[var(--color-fail-bg)]` backgrounds with matching text colors
- [x] 2.2 Verify badges are readable in all states: default, hover, and selected (keyboard + mouse) on the Compare page

## 3. Verification

- [x] 3.1 Manual test: Open model selector on Compare page, scroll with many models — confirm buttons stay sticky and badges are readable on hover/select
- [x] 3.2 Confirm existing behavior preserved: selection, deselection, "Select all", "Clear", search filtering all work as before
