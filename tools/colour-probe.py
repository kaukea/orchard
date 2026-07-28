#!/usr/bin/env python3
"""Print candidate foreground colours over a real sidebar background, each
one measured three different ways, so a human can say which are readable.

The point is that the three measures disagree, and they disagree most on
exactly the dark backgrounds this sidebar uses:

  WCAG    the (L+0.05) ratio the renderer enforces today. Its additive term
          dominates at low luminance, so it flatters dark pairs and reports
          comfortable numbers for text nobody can read.
  dL*     difference in CIELAB lightness — perceptually uniform, so a given
          difference means roughly the same amount of "lighter" anywhere in
          the range. No standard threshold; a useful rule of thumb is 40+
          for body text.
  APCA    lightness contrast from the WCAG 3 draft, built specifically
          because the ratio misjudges dark backgrounds. Polarity matters:
          light text on dark reports negative, and roughly |Lc| 60 is body
          text, 75 is comfortable.

Usage:  python3 tools/colour-probe.py [row]     row: stale (default) | task | step
"""

import sys
import os
import colorsys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sidebar_colour as sc


# ---------------------------------------------------------------- measures

def wcag(fg, bg):
    return sc.contrast_ratio(fg, bg)


def _srgb_to_xyz_component(v):
    v /= 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def lab_lightness(rgb):
    """CIELAB L*, 0 (black) to 100 (white)."""
    r, g, b = (_srgb_to_xyz_component(c) for c in rgb)
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    e, k = 216 / 24389, 24389 / 27
    fy = y ** (1 / 3) if y > e else (k * y + 16) / 116
    return 116 * fy - 16


def delta_lstar(fg, bg):
    return abs(lab_lightness(fg) - lab_lightness(bg))


def apca_lc(fg, bg):
    """APCA lightness contrast. Negative means light text on dark."""
    def y(rgb):
        return (0.2126729 * (rgb[0] / 255) ** 2.4
                + 0.7151522 * (rgb[1] / 255) ** 2.4
                + 0.0721750 * (rgb[2] / 255) ** 2.4)

    ytxt, ybg = y(fg), y(bg)
    clamp = lambda v: 0.0 if v < 0.022 else v
    ytxt, ybg = clamp(ytxt), clamp(ybg)
    if ybg > ytxt:                                    # dark text on light
        s = (ybg ** 0.56 - ytxt ** 0.57) * 1.14
        lc = 0.0 if abs(s) < 0.1 else s - 0.027
    else:                                             # light text on dark
        s = (ybg ** 0.65 - ytxt ** 0.62) * 1.14
        lc = 0.0 if abs(s) < 0.1 else s + 0.027
    return lc * 100


# ---------------------------------------------------------------- swatches

def swatch(fg, bg, text, bold=False):
    b = "\x1b[1m" if bold else ""
    return (f"\x1b[38;2;{fg[0]};{fg[1]};{fg[2]}m"
            f"\x1b[48;2;{bg[0]};{bg[1]};{bg[2]}m{b}{text}\x1b[0m")


def ladder(bg, hue, chroma_pct, count=12):
    """Candidate foregrounds at one hue, walking lightness AWAY from the
    background.

    Direction is chosen from the background rather than assumed: a task row
    carries its own identity colour, and those run from pale cyan to bright
    magenta to near-black, so a fixed ladder is upside down for half of
    them. The range deliberately overshoots what the sidebar uses today,
    because on several of these backgrounds the comfortable end sits well
    past anything currently on screen.
    """
    dark_bg = lab_lightness(bg) < 50
    lo, hi = (0.34, 0.93) if dark_bg else (0.04, 0.52)
    out = []
    for i in range(count):
        l = lo + i * (hi - lo) / (count - 1)
        r, g, b = colorsys.hls_to_rgb(hue, l, chroma_pct)
        out.append((round(r * 255), round(g * 255), round(b * 255)))
    return out


ROWS = {
    "stale": "the stale entry — the one you said is impossible to read",
    "task": "a task row",
    "step": "a step row",
}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "stale"
    if "," in arg:                      # an explicit background: "203,111,205"
        bg = tuple(int(p) for p in arg.split(","))
        label = "the background you gave me"
    else:
        hue = sc._repo_hue("orchids")
        roles = sc.repo_colour_roles(hue)
        bg = {"stale": roles.third, "task": roles.third,
              "step": roles.fourth}[arg]
        label = ROWS[arg]

    print(f"\nBackground for {label}: rgb{bg}  "
          f"L*={lab_lightness(bg):.1f}  "
          f"({'dark — light text' if lab_lightness(bg) < 50 else 'light — dark text'})\n")
    print("Each line is the SAME text in a different foreground. Read them, "
          "ignore the numbers,\nand tell me the first one that is comfortable "
          "and the first one that is legible at all.\n")

    header = f"{'#':>2}  {'rgb':<16} {'WCAG':>6} {'dL*':>6} {'APCA':>7}   sample"
    print(header)
    print("-" * len(header) + "-" * 30)

    magenta_hue = 0.87
    for i, fg in enumerate(ladder(bg, magenta_hue, 0.55), 1):
        line = (f"{i:>2}  {str(fg):<16} {wcag(fg, bg):>6.2f} "
                f"{delta_lstar(fg, bg):>6.1f} {apca_lc(fg, bg):>7.1f}   ")
        line += swatch(fg, bg, " stale after long silence ")
        line += "  " + swatch(fg, bg, " bold ", bold=True)
        print(line)

    print("\nSame ladder, desaturated — less colour, more lightness:\n")
    for i, fg in enumerate(ladder(bg, magenta_hue, 0.18), 1):
        line = (f"{i:>2}  {str(fg):<16} {wcag(fg, bg):>6.2f} "
                f"{delta_lstar(fg, bg):>6.1f} {apca_lc(fg, bg):>7.1f}   ")
        line += swatch(fg, bg, " stale after long silence ")
        line += "  " + swatch(fg, bg, " bold ", bold=True)
        print(line)

    print("\nFor reference, what the renderer draws there today:\n")
    for name, fg in (("MUTED", sc.MUTED), ("TEXT", sc.TEXT)):
        line = (f"{name:>10}  {str(fg):<16} {wcag(fg, bg):>6.2f} "
                f"{delta_lstar(fg, bg):>6.1f} {apca_lc(fg, bg):>7.1f}   ")
        line += swatch(fg, bg, " stale after long silence ")
        line += "  " + swatch(fg, bg, " bold ", bold=True)
        print(line)
    print()


if __name__ == "__main__":
    main()
