#!/usr/bin/env python3
"""Show one sample of each candidate palette so a human can choose.

Every palette here is under a licence that permits commercial
redistribution, because this project is to be dual-licensed: non-commercial
by default, with paid commercial licences available, and the result must be
shippable inside a commercial product alongside the open one. That rules out
anything non-commercial or share-alike, and it specifically rules out
Pantone, whose colour references are licensed and enforced.

Each palette prints its accent colours as row backgrounds with its own text
colour on top, which is how the sidebar would actually use them, and each
sample carries its APCA lightness contrast so taste and readability can be
judged in the same glance. Roughly 60 is body text, 75 is comfortable.

The hex values are transcribed and should be verified against each upstream
source before any of them is vendored.

Usage:  python3 tools/palette-probe.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util as _u

_spec = _u.spec_from_file_location(
    "colour_probe", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "colour-probe.py"))
_probe = _u.module_from_spec(_spec)
_spec.loader.exec_module(_probe)

apca_lc = _probe.apca_lc


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


PALETTES = [
    ("Open Color", "MIT", "13 hues x 10 tones, built for user interfaces",
     "#212529", "#f8f9fa",
     ["#fa5252", "#e64980", "#be4bdb", "#7950f2", "#4c6ef5", "#228be6",
      "#15aabf", "#12b886", "#40c057", "#82c91e", "#fab005", "#fd7e14"]),

    ("Tailwind", "MIT", "22 hues x 11 tones, the widest range of these",
     "#0f172a", "#f8fafc",
     ["#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e", "#14b8a6",
      "#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6", "#d946ef", "#ec4899"]),

    ("Catppuccin Mocha", "MIT", "designed by and for terminal users",
     "#1e1e2e", "#cdd6f4",
     ["#f38ba8", "#eba0ac", "#fab387", "#f9e2af", "#a6e3a1", "#94e2d5",
      "#89dceb", "#74c7ec", "#89b4fa", "#b4befe", "#cba6f7", "#f5c2e7"]),

    ("Rose Pine", "MIT", "muted and warm, fewer accents",
     "#191724", "#e0def4",
     ["#eb6f92", "#f6c177", "#ebbcba", "#31748f", "#9ccfd8", "#c4a7e7"]),

    ("Nord", "MIT", "cool and restrained, arctic palette",
     "#2e3440", "#eceff4",
     ["#bf616a", "#d08770", "#ebcb8b", "#a3be8c", "#b48ead", "#8fbcbb",
      "#88c0d0", "#81a1c1", "#5e81ac"]),

    ("Dracula", "MIT", "high saturation, high contrast",
     "#282a36", "#f8f8f2",
     ["#ff5555", "#ffb86c", "#f1fa8c", "#50fa7b", "#8be9fd", "#bd93f9",
      "#ff79c6"]),

    ("Solarized", "MIT", "the oldest of these, precision-tuned lightness",
     "#002b36", "#93a1a1",
     ["#b58900", "#cb4b16", "#dc322f", "#d33682", "#6c71c4", "#268bd2",
      "#2aa198", "#859900"]),
]


def swatch(fg, bg, text):
    return (f"\x1b[38;2;{fg[0]};{fg[1]};{fg[2]}m"
            f"\x1b[48;2;{bg[0]};{bg[1]};{bg[2]}m{text}\x1b[0m")


def main():
    print("\nOne sample of each. Every licence below permits commercial "
          "redistribution.\n"
          "Each accent is shown as a row background carrying that palette's "
          "own text colour,\nwhich is how the sidebar would use it. The "
          "number is APCA lightness contrast:\n"
          "about 60 is body text, 75 is comfortable.\n")

    for name, licence, note, dark, light, accents in PALETTES:
        dark_rgb, light_rgb = rgb(dark), rgb(light)
        print(f"\n\x1b[1m{name}\x1b[0m  ({licence}) — {note}")
        print(f"  {len(accents)} accents shown"
              f"{'' if len(accents) >= 7 else '  ** fewer than seven **'}")
        for hexval in accents:
            bg = rgb(hexval)
            on_dark, on_light = apca_lc(dark_rgb, bg), apca_lc(light_rgb, bg)
            best_fg, best = ((dark_rgb, on_dark)
                             if abs(on_dark) >= abs(on_light)
                             else (light_rgb, on_light))
            print(f"    {hexval}  APCA {abs(best):5.1f}  "
                  + swatch(best_fg, bg, " a feature name lives here ")
                  + "  "
                  + swatch(bg, dark_rgb, " as an accent on the base "))
    print()


if __name__ == "__main__":
    main()
