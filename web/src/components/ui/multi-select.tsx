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
  renderItemEnd,
  renderItemStart,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const selectedSet = new Set(value);
  const normalizedSearch = search.trim().toLowerCase();
  const filteredOptions = useMemo(() => {
    if (!normalizedSearch) return options;
    return options.filter((option) => {
      const haystack = [option.value, option.label, ...(option.keywords ?? [])]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedSearch);
    });
  }, [normalizedSearch, options]);

  const toggle = useCallback(
    (val: string) => {
      if (selectedSet.has(val)) {
        onChange(value.filter((v) => v !== val));
      } else {
        onChange([...value, val]);
      }
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
          className={cn(
            "brand-select flex w-full items-center justify-between gap-2 px-3 py-2 whitespace-nowrap",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "h-9 min-h-9",
            "[&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
            className
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
        className="w-(--radix-popover-trigger-width) p-0 border-2 border-border shadow"
        align="start"
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={searchPlaceholder}
            value={search}
            onValueChange={setSearch}
          />
          <div className="flex items-center gap-2 px-2 py-1.5 shrink-0">
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => onChange(filteredOptions.map((o) => o.value))}
            >
              Select all
            </button>
            <span className="text-border text-xs">·</span>
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => onChange([])}
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
