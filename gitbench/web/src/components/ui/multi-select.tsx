import { useState, useCallback, type ReactNode } from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
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
  const selectedSet = new Set(value);

  const toggle = useCallback(
    (val: string) => {
      if (selectedSet.has(val)) {
        onChange(value.filter((v) => v !== val));
      } else {
        onChange([...value, val]);
      }
    },
    [value, onChange],
  );

  const remove = useCallback(
    (val: string) => {
      onChange(value.filter((v) => v !== val));
    },
    [value, onChange],
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
            "flex w-full items-center justify-between gap-2 rounded-md border border-input bg-transparent px-3 py-2 text-sm whitespace-nowrap transition-[color,box-shadow] outline-none",
            "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "dark:bg-input/30 dark:hover:bg-input/50",
            "h-9 min-h-9",
            "[&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
            className,
          )}
        >
          <span className="flex items-center gap-1.5 flex-wrap min-w-0">
            {selectedOptions.length === 0 ? (
              <span className="text-muted-foreground">{placeholder}</span>
            ) : selectedOptions.length <= 2 ? (
              selectedOptions.map((o) => (
                <Badge
                  key={o.value}
                  variant="secondary"
                  className="font-mono"
                >
                  {o.label}
                  <X
                    className="ml-0.5 h-3 w-3 cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation();
                      remove(o.value);
                    }}
                    aria-label={`Remove ${o.label}`}
                  />
                </Badge>
              ))
            ) : (
              <span>{selectedOptions.length} selected</span>
            )}
          </span>
          <ChevronsUpDown className="size-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[--radix-popover-trigger-width] p-0"
        align="start"
      >
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyMessage}</CommandEmpty>
            <CommandGroup>
              <div className="flex items-center gap-2 px-2 py-1.5">
                <button
                  type="button"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => onChange(options.map((o) => o.value))}
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
              {options.map((option) => {
                const isSelected = selectedSet.has(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    value={option.value}
                    onSelect={() => toggle(option.value)}
                    className="pr-8"
                  >
                    <span className="flex-1">{renderItemStart?.(option)}{option.label}</span>
                    {renderItemEnd?.(option)}
                    {isSelected && (
                      <Check className="absolute right-2 h-4 w-4" />
                    )}
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
