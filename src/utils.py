from colorsys import rgb_to_hls
import re


def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))


def relative_luminance(rgb):
    def channel_lum(c):
        return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    r, g, b = rgb
    return 0.2126*channel_lum(r) + 0.7152*channel_lum(g) + 0.0722*channel_lum(b)


def contrast_ratio(hex1, hex2):
    lum1 = relative_luminance(hex_to_rgb(hex1))
    lum2 = relative_luminance(hex_to_rgb(hex2))
    L1, L2 = max(lum1, lum2), min(lum1, lum2)
    return (L1 + 0.05) / (L2 + 0.05)


def is_colorblind_safe(palette):
    # Simplistic check: ensure no red-green pairs
    rgb_vals = [hex_to_rgb(c) for c in palette]
    for (r1, g1, b1), (r2, g2, b2) in zip(rgb_vals, rgb_vals[1:]):
        if abs(r1 - g1) < 0.2 and abs(r2 - g2) < 0.2:  # red-green confusion
            return False
    return True


def lint_color_contrast(palette, background='#ffffff'):
    results = []
    for color in palette:
        ratio = contrast_ratio(color, background)
        results.append((color, ratio, ratio >= 4.5))
    return results


# Example usage:
if __name__ == '__main__':
    palette = ['#1f77b4', '#aec7e8', '#ff7f0e', '#2ca02c']
    print('Colorblind safe:', is_colorblind_safe(palette))
    print('Contrast vs white:')
    for c, r, ok in lint_color_contrast(palette):
        print(f'  {c}: {r:.2f} → {"PASS" if ok else "FAIL"}')
