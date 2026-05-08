# ANSI color codes
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RESET = "\x1b[0m"
BOLD = "\x1b[1m"

# Cached color detection result
_use_colors: bool | None = None


def should_use_colors(stream=None) -> bool:
    """Determine whether to use colored terminal output.

    Checks:
    - NO_COLOR environment variable (per https://no-color.org/)
    - TERM environment variable set to 'dumb'
    - Whether the stream is a TTY

    Result is cached after first call for performance when no stream argument
    is provided.

    Args:
        stream: Stream to check TTY status against.  Defaults to sys.stdout.

    Returns:
        True if colors should be used, False otherwise.
    """
    global _use_colors
    import os

    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        _use_colors = False
        return False

    if stream is not None:
        return bool(getattr(stream, "isatty", lambda: False)())

    if _use_colors is not None:
        return _use_colors

    import sys
    check_stream = stream or sys.stdout
    is_tty = getattr(check_stream, "isatty", lambda: False)()
    _use_colors = bool(is_tty)
    return _use_colors


def is_output_suppressed(stream=None) -> bool:
    """Determine whether TTY-only output should be suppressed.

    TTY-only output (e.g. summary table) should only print when stdout is a
    real terminal, not when piped or redirected.  This differs from color
    detection in that we never suppress just because of NO_COLOR or
    TERM=dumb — those only disable colors, not the output itself.

    Args:
        stream: Stream to check TTY status against.  Defaults to sys.stdout.

    Returns:
        True if TTY-only output should be suppressed, False if it should
        print.
    """
    import sys
    check_stream = stream or sys.stdout
    return not bool(getattr(check_stream, "isatty", lambda: False)())
