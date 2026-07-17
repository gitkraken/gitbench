import { useState, useCallback, useMemo, type ReactNode } from "react";
import { Check, ChevronsUpDown, Square } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import {
  clearMultiSelectValues,
  filterMultiSelectOptions,
  selectAllMultiSelectValues,
  toggleMultiSelectValue,
} from "@/lib/multi-select-state";

export interface MultiSelectOption {
  value: string;
  label: string;
  keywords?: string[];
}

export interface MultiSelectProps {
  options: MultiSelectOption[];
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  className?: string;
  triggerClassName?: string;
  panelClassName?: string;
  headerContent?: ReactNode;
  ariaLabel?: string;
  /** Render extra content next to each item in the dropdown */
  renderItemEnd?: (option: MultiSelectOption) => ReactNode;
  /** Render content before the label in each dropdown item */
  renderItemStart?: (option: MultiSelectOption) => ReactNode;
}

export function MultiSelect({
  options,
  value,
  onChange,
  placeholder = "Select items...",
  searchPlaceholder = "Search...",
  emptyMessage = "No items found.",
  className,
  triggerClassName,
  panelClassName,
  headerContent,
  ariaLabel,
  renderItemEnd,
  renderItemStart,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const selectedSet = new Set(value);
  const filteredOptions = useMemo(
    () => filterMultiSelectOptions(options, search),
    [search, options],
  );

  const toggle = useCallback(
    (val: string) => {
      onChange(toggleMultiSelectValue(value, val));
    },
    [value, onChange]
  );

  const selectedOptions = options.filter((o) => selectedSet.has(o.value));

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          role="combobox"
          aria-expanded={open}
          aria-label={ariaLabel ?? placeholder}
          className={cn(
            "brand-select flex w-full items-center justify-between gap-2 px-3 py-2 whitespace-nowrap",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "h-9 min-h-9",
            "[&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
            className,
            triggerClassName,
          )}
        >
          <span className="min-w-0 truncate">
            {selectedOptions.length === 0 ? (
              <span className="text-muted-foreground">{placeholder}</span>
            ) : (
              <span>{selectedOptions.length} selected</span>
            )}
          </span>
          <ChevronsUpDown className="size-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className={cn(
          "w-(--radix-popover-trigger-width) max-w-[calc(100vw-2rem)] overflow-hidden p-0 border-2 border-border shadow",
          panelClassName,
        )}
        align="start"
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={searchPlaceholder}
            value={search}
            onValueChange={setSearch}
          />
          {headerContent ? (
            <>
              <div className="shrink-0">{headerContent}</div>
              <CommandSeparator />
            </>
          ) : null}
          <div className="flex items-center gap-2 px-2 py-1.5 shrink-0">
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              onKeyDown={(event) => event.stopPropagation()}
              onClick={() => onChange(selectAllMultiSelectValues(filteredOptions))}
            >
              Select all
            </button>
            <span className="text-border text-xs">·</span>
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              onKeyDown={(event) => event.stopPropagation()}
              onClick={() => onChange(clearMultiSelectValues())}
            >
              Clear
            </button>
          </div>
          <CommandSeparator />
          <CommandList>
            <CommandEmpty>{emptyMessage}</CommandEmpty>
            <CommandGroup>
              {filteredOptions.map((option) => {
                const isSelected = selectedSet.has(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    value={option.value}
                    onSelect={() => toggle(option.value)}
                    aria-label={`${option.label}${isSelected ? ", selected" : ""}`}
                  >
                    <span className="flex min-w-0 flex-1 items-center">
                      <span className="mr-2 inline-flex size-4 shrink-0 items-center justify-center rounded-[3px] border border-input">
                        {isSelected ? (
                          <Check className="size-3" />
                        ) : (
                          <Square className="size-3 opacity-0" />
                        )}
                      </span>
                      {renderItemStart?.(option)}
                      <span className="truncate">{option.label}</span>
                    </span>
                    {renderItemEnd?.(option)}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
