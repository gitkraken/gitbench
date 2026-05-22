import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-[5px] font-bold whitespace-nowrap transition-all outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-[linear-gradient(97deg,#7900C9_19.46%,#2B5FFE_109.79%)] text-white hover:bg-[linear-gradient(97deg,#7D14F7_19.46%,#1970FF_109.79%)] hover:shadow-[0_5px_15px_rgba(0,0,0,0.35)]",
        destructive:
          "bg-destructive text-white hover:bg-destructive/90 focus-visible:ring-destructive/20 dark:bg-destructive/60 dark:focus-visible:ring-destructive/40",
        outline:
          "border-2 border-[#7900C9] bg-transparent text-white shadow-xs hover:border-white hover:bg-transparent hover:text-white hover:shadow-[0_5px_15px_rgba(0,0,0,0.35)] dark:border-[#7900C9] dark:bg-transparent dark:hover:bg-transparent",
        secondary:
          "border-2 border-[#7900C9] bg-transparent text-white hover:border-white hover:bg-transparent hover:text-white",
        ghost:
          "text-white hover:bg-white/10 hover:text-white dark:hover:bg-white/10",
        link: "text-[#EC7FFF] underline-offset-4 hover:text-[#C170FF] hover:underline",
      },
      size: {
        default: "h-auto min-h-10 px-5 py-3 text-sm leading-5 has-[>svg]:px-3",
        xs: "h-7 gap-1 rounded-[5px] px-2.5 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 rounded-[5px] px-3.5 text-xs has-[>svg]:px-2.5",
        lg: "h-auto min-h-12 rounded-[5px] px-6 py-4 text-base leading-6 has-[>svg]:px-4",
        icon: "size-9",
        "icon-xs": "size-7 rounded-[5px] [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8",
        "icon-lg": "size-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "button";

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
