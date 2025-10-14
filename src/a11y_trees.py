import re


class ColorAccessibility:
    """Checks related to color usage in charts."""

    def __init__(self, palette, background="#ffffff"):
        self.palette = palette
        self.background = background

    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple normalized to [0,1]."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4))

    def is_colorblind_safe(self, palette):
        """Rudimentary check for red-green colorblind safety.
        Simplistic check: ensure no red-green pairs
        """
        rgb_vals = [self.hex_to_rgb(c) for c in palette]
        for (r1, g1, b1), (r2, g2, b2) in zip(rgb_vals, rgb_vals[1:]):
            if abs(r1 - g1) < 0.2 and abs(r2 - g2) < 0.2:  # red-green confusion
                return False
        return True

    def relative_luminance(self, rgb):
        """Calculate relative luminance of an RGB color."""
        def channel_lum(c):
            return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
        r, g, b = rgb
        return 0.2126*channel_lum(r) + 0.7152*channel_lum(g) + 0.0722*channel_lum(b)

    def contrast_ratio(self, hex1, hex2):
        """Calculate contrast ratio between two hex colors."""
        lum1 = self.relative_luminance(self.hex_to_rgb(hex1))
        lum2 = self.relative_luminance(self.hex_to_rgb(hex2))
        L1, L2 = max(lum1, lum2), min(lum1, lum2)
        return (L1 + 0.05) / (L2 + 0.05)

    def check_palette_safety(self):
        """Check if palette is colorblind-safe."""
        safe = self.is_colorblind_safe(self.palette)
        return {"safe": safe, "message": "Colorblind-safe" if safe else "Red/Green confusion risk"}

    def check_background_contrast(self):
        """Check contrast of each color against background."""
        results = []
        for c in self.palette:
            ratio = self.contrast_ratio(c, self.background)
            results.append({"color": c, "ratio": round(
                ratio, 2), "pass": ratio >= 4.5})
        return results

    def check_adjacent_contrast(self):
        """Check contrast between adjacent colors in the palette."""
        results = []
        for i in range(len(self.palette)-1):
            c1, c2 = self.palette[i], self.palette[i+1]
            ratio = self.contrast_ratio(c1, c2)
            results.append({"pair": (c1, c2), "ratio": round(
                ratio, 2), "pass": ratio >= 3.0})
        return results

    def check_grayscale(self):
        """Check if colors remain distinct in grayscale."""
        lums = [round(self.relative_luminance(self.hex_to_rgb(c)), 2)
                for c in self.palette]
        return {"unique": len(set(lums)) == len(lums), "luminances": lums}

    def run_all(self):
        """Run all color accessibility checks."""
        return {
            "palette_safety": self.check_palette_safety(),
            "background_contrast": self.check_background_contrast(),
            "adjacent_contrast": self.check_adjacent_contrast(),
            "grayscale_test": self.check_grayscale()
        }


class ScreenReaderAccessibility:
    """Checks related to screen reader accessibility."""
    def __init__(self, chart_html):
        self.html = chart_html

    def has_alt_text(self):
        """Check for alt text in images and descriptions in SVG.
        Matches alt="" or <desc> in SVG
        """
        has_img_alt = bool(re.search(r'<img[^>]+alt="[^"]+"', self.html))
        has_desc = bool(re.search(r'<desc>.*?</desc>', self.html, re.DOTALL))
        return {"has_img_alt": has_img_alt, "has_desc": has_desc}

    def aria_roles(self):
        """Extract ARIA roles from the HTML."""
        roles = re.findall(r'role="([^"]+)"', self.html)
        return {"roles": roles}

    def semantic_table(self):
        """Check for <table> presence with headers."""
        has_table = "<table" in self.html
        has_th = "<th" in self.html
        return {"has_table": has_table, "has_th": has_th}

    def run_all(self):
        """Run all screen reader accessibility checks."""
        return {
            "alt_text": self.has_alt_text(),
            "aria_roles": self.aria_roles(),
            "semantic_table": self.semantic_table()
        }


class CognitiveAccessibility:
    """Checks related to cognitive accessibility."""
    def __init__(self, chart_elements):
        # list of element counts, e.g. series count, gridlines count
        self.elements = chart_elements

    def element_count(self):
        """Check number of series and gridlines."""
        return {"series": self.elements.get("series", 0), "gridlines": self.elements.get("gridlines", 0)}

    def legend_entries(self):
        """Check number of legend entries."""
        count = self.elements.get("legend_entries", 0)
        return {"legend_entries": count, "pass": count <= 6}

    def layout_complexity(self):
        """Assess layout complexity based on visual encodings."""
        # heuristic: total distinct visual encodings > threshold
        encodings = self.elements.get("encodings", 0)
        return {"encodings": encodings, "pass": encodings <= 4}

    def run_all(self):
        """Run all cognitive accessibility checks."""
        return {
            "element_count": self.element_count(),
            "legend_entries": self.legend_entries(),
            "layout_complexity": self.layout_complexity()
        }


class MotorAccessibility:
    """Checks related to motor accessibility."""
    def __init__(self, interactions):
        self.interactions = interactions  # dict: keyboard, touch_targets, focus_styles

    def keyboard_support(self):
        """Check for keyboard interaction support."""
        return {"keyboard": self.interactions.get("keyboard", False)}

    def touch_targets(self):
        """Check touch target sizes."""
        sizes = self.interactions.get("touch_targets", [])
        pass_all = all(size >= 44 for size in sizes)
        return {"touch_sizes": sizes, "pass": pass_all}

    def focus_indicators(self):
        """Check for visible focus indicators."""
        return {"focus_indicators": self.interactions.get("focus_indicators", False)}

    def run_all(self):
        """Run all motor accessibility checks."""
        return {
            "keyboard_support": self.keyboard_support(),
            "touch_targets": self.touch_targets(),
            "focus_indicators": self.focus_indicators()
        }


class ResponsiveAccessibility:
    """Checks related to responsive accessibility."""
    def __init__(self, chart_props):
        self.props = chart_props  # dict: zoom_behavior, mobile_layout, svg_scalable

    def zoom_behavior(self):
        """Check zoom behavior for accessibility."""
        return {"zoom_200": self.props.get("zoom_200", False)}

    def mobile_layout(self):
        """Check mobile layout for accessibility."""
        return {"mobile_adaptive": self.props.get("mobile_adaptive", False)}

    def svg_scalable(self):
        """Check if SVG is scalable."""
        return {"svg_scalable": self.props.get("svg_scalable", False)}

    def run_all(self):
        """Run all responsive accessibility checks."""
        return {
            "zoom_behavior": self.zoom_behavior(),
            "mobile_layout": self.mobile_layout(),
            "svg_scalable": self.svg_scalable()
        }


if __name__ == "__main__":
    # Color example
    palette = ["#1f77b4", "#aec7e8", "#ff7f0e"]
    color_tree = ColorAccessibility(palette)
    print("Color checks:", color_tree.run_all())

    # Screen reader example
    html = '<svg><desc>Bar chart of sales</desc></svg>'
    sr_tree = ScreenReaderAccessibility(html)
    print("Screen reader checks:", sr_tree.run_all())

    # Cognitive example
    elems = {"series": 3, "gridlines": 4, "legend_entries": 5, "encodings": 3}
    cog_tree = CognitiveAccessibility(elems)
    print("Cognitive checks:", cog_tree.run_all())

    # Motor example
    interactions = {"keyboard": True, "touch_targets": [
        50, 45, 60], "focus_indicators": True}
    motor_tree = MotorAccessibility(interactions)
    print("Motor checks:", motor_tree.run_all())

    # Responsive example
    props = {"zoom_200": True, "mobile_adaptive": True, "svg_scalable": True}
    resp_tree = ResponsiveAccessibility(props)
    print("Responsive checks:", resp_tree.run_all())
