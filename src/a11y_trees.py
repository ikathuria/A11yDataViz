import re
from colorsys import rgb_to_hls
from utils import (
    hex_to_rgb,
    relative_luminance,
    contrast_ratio,
    is_colorblind_safe
)


class ColorAccessibility:
    def __init__(self, palette, background="#ffffff"):
        self.palette = palette
        self.background = background

    def check_palette_safety(self):
        safe = is_colorblind_safe(self.palette)
        return {"safe": safe, "message": "Colorblind-safe" if safe else "Red/Green confusion risk"}

    def check_background_contrast(self):
        results = []
        for c in self.palette:
            ratio = contrast_ratio(c, self.background)
            results.append({"color": c, "ratio": round(
                ratio, 2), "pass": ratio >= 4.5})
        return results

    def check_adjacent_contrast(self):
        results = []
        for i in range(len(self.palette)-1):
            c1, c2 = self.palette[i], self.palette[i+1]
            ratio = contrast_ratio(c1, c2)
            results.append({"pair": (c1, c2), "ratio": round(
                ratio, 2), "pass": ratio >= 3.0})
        return results

    def check_grayscale(self):
        lums = [round(relative_luminance(hex_to_rgb(c)), 2)
                for c in self.palette]
        return {"unique": len(set(lums)) == len(lums), "luminances": lums}

    def run_all(self):
        return {
            "palette_safety": self.check_palette_safety(),
            "background_contrast": self.check_background_contrast(),
            "adjacent_contrast": self.check_adjacent_contrast(),
            "grayscale_test": self.check_grayscale()
        }


class ScreenReaderAccessibility:
    def __init__(self, chart_html):
        self.html = chart_html

    def has_alt_text(self):
        # Matches alt="" or <desc> in SVG
        has_img_alt = bool(re.search(r'<img[^>]+alt="[^"]+"', self.html))
        has_desc = bool(re.search(r'<desc>.*?</desc>', self.html, re.DOTALL))
        return {"has_img_alt": has_img_alt, "has_desc": has_desc}

    def aria_roles(self):
        roles = re.findall(r'role="([^"]+)"', self.html)
        return {"roles": roles}

    def semantic_table(self):
        # Checks for <table> presence with headers
        has_table = "<table" in self.html
        has_th = "<th" in self.html
        return {"has_table": has_table, "has_th": has_th}

    def run_all(self):
        return {
            "alt_text": self.has_alt_text(),
            "aria_roles": self.aria_roles(),
            "semantic_table": self.semantic_table()
        }


class CognitiveAccessibility:
    def __init__(self, chart_elements):
        # list of element counts, e.g. series count, gridlines count
        self.elements = chart_elements

    def element_count(self):
        return {"series": self.elements.get("series", 0), "gridlines": self.elements.get("gridlines", 0)}

    def legend_entries(self):
        count = self.elements.get("legend_entries", 0)
        return {"legend_entries": count, "pass": count <= 6}

    def layout_complexity(self):
        # heuristic: total distinct visual encodings > threshold
        encodings = self.elements.get("encodings", 0)
        return {"encodings": encodings, "pass": encodings <= 4}

    def run_all(self):
        return {
            "element_count": self.element_count(),
            "legend_entries": self.legend_entries(),
            "layout_complexity": self.layout_complexity()
        }


class MotorAccessibility:
    def __init__(self, interactions):
        self.interactions = interactions  # dict: keyboard, touch_targets, focus_styles

    def keyboard_support(self):
        return {"keyboard": self.interactions.get("keyboard", False)}

    def touch_targets(self):
        sizes = self.interactions.get("touch_targets", [])
        pass_all = all(size >= 44 for size in sizes)
        return {"touch_sizes": sizes, "pass": pass_all}

    def focus_indicators(self):
        return {"focus_indicators": self.interactions.get("focus_indicators", False)}

    def run_all(self):
        return {
            "keyboard_support": self.keyboard_support(),
            "touch_targets": self.touch_targets(),
            "focus_indicators": self.focus_indicators()
        }


class ResponsiveAccessibility:
    def __init__(self, chart_props):
        self.props = chart_props  # dict: zoom_behavior, mobile_layout, svg_scalable

    def zoom_behavior(self):
        return {"zoom_200": self.props.get("zoom_200", False)}

    def mobile_layout(self):
        return {"mobile_adaptive": self.props.get("mobile_adaptive", False)}

    def svg_scalable(self):
        return {"svg_scalable": self.props.get("svg_scalable", False)}

    def run_all(self):
        return {
            "zoom_behavior": self.zoom_behavior(),
            "mobile_layout": self.mobile_layout(),
            "svg_scalable": self.svg_scalable()
        }


# Example usage:
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
