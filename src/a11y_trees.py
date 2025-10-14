import re
import json

from utils import grade


class ColorAccessibility:
    """Checks related to color usage in charts."""

    def __init__(self, palette, background="#ffffff"):
        self.palette = palette
        self.background = background

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))

    def relative_luminance(self, rgb):
        def channel_lum(c):
            return c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
        r, g, b = rgb
        return 0.2126*channel_lum(r) + 0.7152*channel_lum(g) + 0.0722*channel_lum(b)

    def contrast_ratio(self, hex1, hex2):
        lum1 = self.relative_luminance(self.hex_to_rgb(hex1))
        lum2 = self.relative_luminance(self.hex_to_rgb(hex2))
        L1, L2 = max(lum1, lum2), min(lum1, lum2)
        return (L1 + 0.05) / (L2 + 0.05)

    def is_colorblind_safe(self, palette):
        rgb_vals = [self.hex_to_rgb(c) for c in palette]
        issues = 0
        for i, (r1, g1, b1) in enumerate(rgb_vals):
            for (r2, g2, b2) in rgb_vals[i+1:]:
                if abs(r1 - g1) < 0.15 and abs(r2 - g2) < 0.15:
                    issues += 1
                if abs(b1 - (r1+g1)/2) < 0.15 and abs(b2 - (r2+g2)/2) < 0.15:
                    issues += 1
        if issues == 0:
            return {"score": 3, "safe": True, "message": "Fully colorblind-safe"}
        elif issues <= 2:
            return {"score": 2, "safe": False, "message": f"{issues} potential confusion pairs"}
        else:
            return {"score": 0, "safe": False, "message": f"{issues} confusion pairs - high risk"}

    def check_palette_safety(self):
        return self.is_colorblind_safe(self.palette)

    def check_background_contrast(self):
        results, pass_count = [], 0
        for c in self.palette:
            ratio = self.contrast_ratio(c, self.background)
            passed = ratio >= 4.5
            pass_count += passed
            results.append(
                {"color": c, "ratio": round(ratio, 2), "pass": passed})
        rate = pass_count / len(self.palette)
        if rate >= 0.9:
            score = 3
        elif rate >= 0.7:
            score = 2
        elif rate >= 0.4:
            score = 1
        else:
            score = 0
        return {"score": score, "details": results, "pass_rate": round(rate*100, 1)}

    def check_adjacent_contrast(self):
        results, pass_count = [], 0
        pairs = zip(self.palette, self.palette[1:])
        for c1, c2 in pairs:
            ratio = self.contrast_ratio(c1, c2)
            passed = ratio >= 3.0
            pass_count += passed
            results.append(
                {"pair": (c1, c2), "ratio": round(ratio, 2), "pass": passed})
        total = len(results) or 1
        rate = pass_count / total
        if rate >= 0.9:
            score = 3
        elif rate >= 0.7:
            score = 2
        elif rate >= 0.4:
            score = 1
        else:
            score = 0
        return {"score": score, "details": results, "pass_rate": round(rate*100, 1)}

    def check_grayscale(self):
        lums = [round(self.relative_luminance(self.hex_to_rgb(c)), 2)
                for c in self.palette]
        unique = len(set(lums)) == len(lums)
        total, uniq = len(lums), len(set(lums))
        if unique:
            score = 3
        elif uniq >= total*0.8:
            score = 2
        elif uniq >= total*0.5:
            score = 1
        else:
            score = 0
        return {"score": score, "unique": unique, "luminances": lums}

    def check_pattern_encoding(self, has_patterns):
        if has_patterns:
            return {"score": 3, "message": "Uses patterns/shapes in addition to color"}
        return {"score": 0, "message": "Color is sole encoding - risk"}

    def check_alt_theme(self, alt_palettes):
        if alt_palettes:
            return {"score": 3, "message": "Alternate themes available"}
        return {"score": 0, "message": "No alternate theme configured"}

    def check_direct_labels(self, chart_html):
        direct = bool(re.search(r'<text[^>]+class="label"', chart_html))
        msg = "Direct labels present" if direct else "No direct labels detected"
        return {"score": 3 if direct else 0, "message": msg}

    def run_all(self, has_patterns=False, alt_palettes=None, chart_html=""):
        checks = {
            "palette_safety": self.check_palette_safety(),
            "background_contrast": self.check_background_contrast(),
            "adjacent_contrast": self.check_adjacent_contrast(),
            "grayscale_test": self.check_grayscale(),
            "pattern_encoding": self.check_pattern_encoding(has_patterns),
            "alt_theme": self.check_alt_theme(alt_palettes or []),
            "direct_labels": self.check_direct_labels(chart_html)
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 21  # 7 checks x 3
        pct = total / max_score * 100
        return {"checks": checks, "summary": {"total_score": total, "max_score": max_score, "percentage": round(pct, 1), "grade": grade(pct)}}


class ScreenReaderAccessibility:
    """Checks related to screen reader accessibility."""

    def __init__(self, chart_html):
        self.html = chart_html

    def has_alt_text(self):
        img_alts = re.findall(r'<img[^>]+alt="([^"]*)"', self.html)
        descs = re.findall(r'<desc>(.*?)</desc>', self.html, re.DOTALL)
        texts = img_alts + [d.strip() for d in descs]
        if not texts or all(not t for t in texts):
            return {"score": 0, "message": "No alt text or descriptions"}
        avg = sum(len(t) for t in texts) / len(texts)
        if avg >= 50:
            return {"score": 3, "message": "Detailed descriptions"}
        if avg >= 20:
            return {"score": 2, "message": "Basic descriptions"}
        return {"score": 1, "message": "Minimal descriptions"}

    def aria_roles(self):
        roles = re.findall(r'role="([^"]+)"', self.html)
        labels = len(re.findall(r'aria-label="[^"]+"', self.html))
        descby = len(re.findall(r'aria-describedby="[^"]+"', self.html))
        score = min(3, (1 if roles else 0) +
                    (1 if labels else 0) + (1 if descby else 0))
        return {"score": score, "roles": roles, "labels": labels, "describedby": descby}

    def semantic_table(self):
        has_table = "<table" in self.html
        has_th = "<th" in self.html
        has_cap = "<caption" in self.html
        has_scope = 'scope="' in self.html
        if not has_table:
            return {"score": 0, "message": "No data table"}
        score = 1 + int(has_th) + int(has_cap or has_scope)
        return {"score": min(score, 3), "headers": has_th, "caption": has_cap}

    def heading_structure(self):
        h = re.findall(r'<h([1-6])', self.html)
        if not h:
            return {"score": 0, "message": "No headings"}
        levels = list(map(int, h))
        seq = all(levels[i+1]-levels[i] <= 1 for i in range(len(levels)-1))
        return {"score": 3 if seq else 2, "levels": levels}

    def check_textual_equivalents(self):
        axes = bool(
            re.search(r'<g[^>]+class="axis"[^>]+aria-labelledby=', self.html))
        legend = bool(
            re.search(r'<g[^>]+class="legend"[^>]+aria-labelledby=', self.html))
        score = 3 if axes and legend else 1 if (axes or legend) else 0
        return {"score": score, "axes": axes, "legend": legend}

    def check_tabindex_order(self):
        tabs = list(map(int, re.findall(r'tabindex="(\d+)"', self.html)))
        seq = tabs == sorted(tabs) if tabs else False
        return {"score": 3 if seq else 0, "order": tabs}

    def run_all(self):
        checks = {
            "alt_text": self.has_alt_text(),
            "aria_roles": self.aria_roles(),
            "semantic_table": self.semantic_table(),
            "heading_structure": self.heading_structure(),
            "textual_equivalents": self.check_textual_equivalents(),
            "tabindex_order": self.check_tabindex_order()
        }
        total = sum(c['score'] for c in checks.values())
        max_score = 18  # 6 checks x 3
        pct = total / max_score * 100
        return {"checks": checks, "summary": {"total_score": total, "max_score": max_score, "percentage": round(pct, 1), "grade": grade(pct)}}


class CognitiveAccessibility:
    """Checks related to cognitive accessibility."""

    def __init__(self, elements):
        self.elements = elements

    def element_count(self):
        s = self.elements.get("series", 0)
        g = self.elements.get("gridlines", 0)
        ss = 3 if s == 1 else 2 if s <= 12 else 1 if s <= 20 else 0
        gs = 3 if g <= 1 else 2 if g <= 3 else 1 if g <= 5 else 0
        final_score = (ss + gs) / 2
        return {"series_score": ss, "gridlines_score": gs, "score": final_score}

    def legend_entries(self):
        c = self.elements.get("legend_entries", 0)
        sc = 3 if c <= 4 else 2 if c <= 6 else 1 if c <= 8 else 0
        return {"count": c, "score": sc}

    def encoding_complexity(self):
        e = self.elements.get("encodings", 0)
        sc = 3 if e <= 2 else 0
        return {"encodings": e, "score": sc}

    def labeling_clarity(self):
        lbls = self.elements.get("labels", [])
        unclear = any(len(lbl) > 20 or re.search(
            r"\b[A-Za-z]{1,3}\b", lbl) for lbl in lbls)
        return {"total_labels": len(lbls), "score": 0 if unclear else 3}

    def check_max_encodings(self):
        return self.encoding_complexity()

    def check_visual_grouping(self, chart_html):
        grp = bool(re.search(r'<g[^>]+class="group"', chart_html))
        return {"score": 3 if grp else 0, "message": "Grouping" if grp else "No grouping"}

    def run_all(self):
        checks = {
            "element_count": self.element_count(),
            "legend_entries": self.legend_entries(),
            "max_encodings": self.check_max_encodings(),
            "labeling_clarity": self.labeling_clarity(),
            "visual_grouping": self.check_visual_grouping(self.elements.get("chart_html", ""))
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 15  # 5x3
        pct = total/max_score*100
        return {"checks": checks, "summary": {"total_score": total, "max_score": max_score, "percentage": round(pct, 1), "grade": grade(pct)}}


class MotorAccessibility:
    """Checks related to motor and interaction accessibility."""

    def __init__(self, interactions):
        self.interactions = interactions

    def keyboard_support(self):
        kb = self.interactions.get("keyboard", False)
        return {"score": 3 if kb else 0, "supported": kb}

    def hover_alternatives(self):
        alt = self.interactions.get("hover_alternatives", False)
        return {"score": 3 if alt else 0, "supported": alt}

    def touch_targets(self):
        sizes = self.interactions.get("touch_targets", [])
        if not sizes:
            return {"sizes": sizes, "score": 0}
        rate = sum(1 for s in sizes if s >= 44)/len(sizes)
        sc = 3 if rate >= 0.9 else 2 if rate >= 0.7 else 1 if rate >= 0.4 else 0
        return {"sizes": sizes, "pass_rate": round(rate*100, 1), "score": sc}

    def focus_indicators(self):
        fi = self.interactions.get("focus_indicators", False)
        return {"score": 3 if fi else 0, "supported": fi}

    def check_skip_links(self):
        html = self.interactions.get("html", "")
        skip = bool(re.search(r'<a[^>]+class="skip"', html))
        return {"score": 3 if skip else 0, "message": "Skip links present" if skip else "No skip links"}

    def run_all(self):
        checks = {
            "keyboard_support": self.keyboard_support(),
            "hover_alternatives": self.hover_alternatives(),
            "touch_targets": self.touch_targets(),
            "focus_indicators": self.focus_indicators(),
            "skip_links": self.check_skip_links()
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 15
        pct = total/max_score*100
        return {"checks": checks, "summary": {"total_score": total, "max_score": max_score, "percentage": round(pct, 1), "grade": grade(pct)}}


class ResponsiveAccessibility:
    """Checks related to responsive and scalable design."""

    def __init__(self, props):
        self.props = props

    def zoom_support(self):
        z = self.props.get("zoom_200", False)
        return {"score": 3 if z else 0, "supported": z}

    def responsive_layout(self):
        r = self.props.get("responsive", False)
        return {"score": 3 if r else 0, "supported": r}

    def text_scaling(self):
        ts = self.props.get("text_scaling", False)
        return {"score": 3 if ts else 0, "supported": ts}

    def vector_graphics(self):
        sv = self.props.get("svg", False)
        return {"score": 3 if sv else 0, "supported": sv}

    def mobile_variant(self):
        mv = self.props.get("mobile_variant", False)
        return {"score": 3 if mv else 0, "supported": mv}

    def check_zoom_tested(self):
        tz = self.props.get("zoom_tested", False)
        return {"score": 3 if tz else 0, "tested": tz}

    def check_font_scaling(self, chart_html):
        px = re.findall(r'font-size:\s*\d+px', chart_html)
        return {"score": 0 if px else 3, "px_found": len(px)}

    def run_all(self):
        checks = {
            "zoom_support": self.zoom_support(),
            "responsive_layout": self.responsive_layout(),
            "text_scaling": self.text_scaling(),
            "vector_graphics": self.vector_graphics(),
            "mobile_variant": self.mobile_variant(),
            "zoom_tested": self.check_zoom_tested(),
            "font_scaling": self.check_font_scaling(self.props.get("chart_html", ""))
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 21
        pct = total/max_score*100
        return {"checks": checks, "summary": {"total_score": total, "max_score": max_score, "percentage": round(pct, 1), "grade": grade(pct)}}
