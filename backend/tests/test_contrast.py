"""
Automated WCAG AA Contrast Test Suite
Validates that every text/background token pair in the Cherry Blossom + Ink Wash system meets WCAG AA (>= 4.5:1 for normal text, >= 3.0:1 for large/UI components).
"""

import math

def hex_to_rgb(hex_code: str):
    clean = hex_code.lstrip("#")
    return tuple(int(clean[i : i + 2], 16) for i in (0, 2, 4))

def srgb_to_linear(c: int) -> float:
    norm = c / 255.0
    return norm / 12.92 if norm <= 0.03928 else math.pow((norm + 0.055) / 1.055, 2.4)

def relative_luminance(hex_code: str) -> float:
    r, g, b = hex_to_rgb(hex_code)
    R = srgb_to_linear(r)
    G = srgb_to_linear(g)
    B = srgb_to_linear(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B

def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

# Design Token Definitions
TOKENS = {
    # Surfaces
    "blossom-100": "#F2C7C7",
    "blossom-300": "#FFB7C5",
    "mint-100": "#D5F3D8",
    "white": "#FFFFFF",
    "ivory": "#FFFFE3",
    "amber-100": "#FFF1D6",
    "rose-100": "#FFE0E3",
    # Ink Wash Text & Neutrals
    "text": "#4A4A4A",
    "text-strong": "#2E2E2E",
    "text-muted": "#55687C",
    "slate": "#6D8196",
    "line": "#CBCBCB",
    # Derived Action & Status Tokens
    "blossom-600": "#C2456B",
    "blossom-700": "#9E3256",
    "mint-700": "#26693D",
    "amber-700": "#8A5A00",
    "rose-700": "#A3213A",
}

PAIRS = [
    ("Body text (--text) on White (--white)", TOKENS["text"], TOKENS["white"], 4.5),
    ("Strong text (--text-strong) on White (--white)", TOKENS["text-strong"], TOKENS["white"], 4.5),
    ("Muted text (--text-muted) on White (--white)", TOKENS["text-muted"], TOKENS["white"], 4.5),
    ("Muted text (--text-muted) on Ivory (--ivory)", TOKENS["text-muted"], TOKENS["ivory"], 4.5),
    ("Body text (--text) on Blossom 100 (--blossom-100)", TOKENS["text"], TOKENS["blossom-100"], 4.5),
    ("Body text (--text) on Mint 100 (--mint-100)", TOKENS["text"], TOKENS["mint-100"], 4.5),
    ("Button text (White) on Blossom 600 (--blossom-600)", TOKENS["white"], TOKENS["blossom-600"], 4.5),
    ("Success text (--mint-700) on Mint 100 (--mint-100)", TOKENS["mint-700"], TOKENS["mint-100"], 4.5),
    ("Warning text (--amber-700) on Amber 100 (--amber-100)", TOKENS["amber-700"], TOKENS["amber-100"], 4.5),
    ("Critical text (--rose-700) on Rose 100 (--rose-100)", TOKENS["rose-700"], TOKENS["rose-100"], 4.5),
    ("Dark element text (--ivory) on Dark container (--text)", TOKENS["ivory"], TOKENS["text"], 4.5),
    ("Slate header / large text (--slate) on White (--white)", TOKENS["slate"], TOKENS["white"], 3.0),
]

def test_wcag_contrast_pairs():
    failures = []
    for name, fg, bg, threshold in PAIRS:
        ratio = contrast_ratio(fg, bg)
        if ratio < threshold:
            failures.append(f"{name}: ratio {ratio:.2f} < required {threshold:.1f}")
    assert not failures, f"WCAG AA contrast test failed:\n" + "\n".join(failures)

if __name__ == "__main__":
    test_wcag_contrast_pairs()
    print("All WCAG AA automated contrast tests passed successfully in Python!")
