import re
import json
from bs4 import BeautifulSoup
from colorspacious import cspace_convert

from utils import grade


class ColorAccessibility:
    """Checks related to color usage in charts."""

    def __init__(
        self,
        palette,
        background="#ffffff",
        contrast_threshold_text=4.5,
        contrast_threshold_graphic=3.0,
        cb_threshold=0.15,
    ):
        """Initialize ColorAccessibility with palette and thresholds.
        
        Args:
            palette: List of hex color codes for the chart palette
            background: Background color in hex format (default: white)
            contrast_threshold_text: Minimum contrast ratio for text (default: 4.5)
            contrast_threshold_graphic: Minimum contrast ratio for graphics (default: 3.0)
            cb_threshold: Threshold for colorblind safety detection (default: 0.15)
        """
        self.palette = palette
        self.background = background
        self.contrast_threshold_text = contrast_threshold_text
        self.contrast_threshold_graphic = contrast_threshold_graphic
        self.cb_threshold = cb_threshold
        self._validate_palette()

    def _validate_palette(self):
        """Validate that all colors in palette and background are valid hex colors.
        
        Raises:
            ValueError: If any color is not a valid 6-digit hex color code
        """
        for c in self.palette + [self.background]:
            if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", c):
                raise ValueError(f"Invalid hex color: {c}")

    def hex_to_rgb(self, hex_color):
        """Convert hex color to normalized RGB values.
        
        Args:
            hex_color: Hex color string (with or without #)
            
        Returns:
            Tuple of RGB values normalized to 0-1 range
        """
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i: i + 2], 16) / 255 for i in (0, 2, 4))

    def relative_luminance(self, rgb):
        """Calculate relative luminance of a color according to WCAG standards.
        
        Args:
            rgb: Tuple of RGB values in 0-1 range
            
        Returns:
            Relative luminance value (0-1)
        """
        def chan(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b = rgb
        return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)

    def contrast_ratio(self, hex1, hex2):
        """Calculate contrast ratio between two colors according to WCAG standards.
        
        Args:
            hex1: First hex color
            hex2: Second hex color
            
        Returns:
            Contrast ratio (1-21, where 21 is maximum contrast)
        """
        lum1 = self.relative_luminance(self.hex_to_rgb(hex1))
        lum2 = self.relative_luminance(self.hex_to_rgb(hex2))
        L1, L2 = max(lum1, lum2), min(lum1, lum2)
        return (L1 + 0.05) / (L2 + 0.05)

    def is_colorblind_safe(self, palette):
        """Check if a color palette is distinguishable for colorblind users.
        
        Uses LAB color space conversion to simulate colorblind perception
        and identify potentially confusing color pairs.
        
        Args:
            palette: List of hex colors to check
            
        Returns:
            Dict with score (0-3), safety status, and descriptive message
        """
        # Use LAB simulation to detect color-distinguishability
        lab = [cspace_convert(self.hex_to_rgb(c), "sRGB1", "CIELab")
               for c in palette]
        issues = 0
        for i, L1_a1_b1 in enumerate(lab):
            for L2_a2_b2 in lab[i + 1:]:
                delta = sum((x - y) ** 2 for x,
                            y in zip(L1_a1_b1, L2_a2_b2)) ** 0.5
                if delta < self.cb_threshold * 100:
                    issues += 1
        if issues == 0:
            return {"score": 3, "safe": True, "message": "Fully colorblind-safe"}
        elif issues <= 2:
            return {"score": 2, "safe": False, "message": f"{issues} potential confusion pairs"}
        else:
            return {"score": 0, "safe": False, "message": f"{issues} confusion pairs - high risk"}

    def check_palette_safety(self):
        """Check colorblind safety of the current palette.
        
        Returns:
            Dict with score, safety status, and message from is_colorblind_safe()
        """
        return self.is_colorblind_safe(self.palette)

    def check_background_contrast(self):
        """Check contrast ratios between palette colors and background.
        
        Evaluates each color in the palette against the background color
        using the text contrast threshold.
        
        Returns:
            Dict with score (0-3), detailed results per color, and pass rate percentage
        """
        results = []
        pass_count = 0
        for c in self.palette:
            ratio = self.contrast_ratio(c, self.background)
            passed = ratio >= self.contrast_threshold_text
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
        return {"score": score, "details": results, "pass_rate": round(rate * 100, 1)}

    def check_adjacent_contrast(self):
        """Check contrast ratios between adjacent colors in the palette.
        
        Tests consecutive color pairs to ensure adequate contrast for
        distinguishability in graphics elements.
        
        Returns:
            Dict with score (0-3), detailed results per pair, and pass rate percentage
        """
        results = []
        pass_count = 0
        for c1, c2 in zip(self.palette, self.palette[1:]):
            ratio = self.contrast_ratio(c1, c2)
            passed = ratio >= self.contrast_threshold_graphic
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
        return {"score": score, "details": results, "pass_rate": round(rate * 100, 1)}

    def check_grayscale(self):
        """Check if colors remain distinguishable when converted to grayscale.
        
        Calculates luminance values for each color and checks for uniqueness
        to ensure the palette works for users who cannot perceive colors.
        
        Returns:
            Dict with score (0-3), uniqueness status, and luminance values
        """
        lums = [
            round(self.relative_luminance(self.hex_to_rgb(c)), 2) for c in self.palette
        ]
        unique = len(set(lums)) == len(lums)
        total, uniq = len(lums), len(set(lums))
        if unique:
            score = 3
        elif uniq >= total * 0.8:
            score = 2
        elif uniq >= total * 0.5:
            score = 1
        else:
            score = 0
        return {"score": score, "unique": unique, "luminances": lums}

    def check_pattern_encoding(self, has_patterns):
        """Check if the visualization uses patterns/shapes in addition to color.
        
        Args:
            has_patterns: Boolean indicating if patterns or shapes are used
            
        Returns:
            Dict with score (0 or 3) and descriptive message
        """
        if has_patterns:
            return {"score": 3, "message": "Uses patterns/shapes in addition to color"}
        return {"score": 0, "message": "Color is sole encoding - risk"}

    def check_alt_theme(self, alt_palettes):
        """Check if alternative color themes are available.
        
        Args:
            alt_palettes: List of alternative color palettes
            
        Returns:
            Dict with score (0 or 3) and descriptive message
        """
        if alt_palettes:
            return {"score": 3, "message": "Alternate themes available"}
        return {"score": 0, "message": "No alternate theme configured"}

    def check_direct_labels(self, chart_html):
        """Check if the chart uses direct labels on data elements.
        
        Args:
            chart_html: HTML content of the chart to analyze
            
        Returns:
            Dict with score (0 or 3) and descriptive message
        """
        soup = BeautifulSoup(chart_html, "html.parser")
        labels = soup.find_all(class_="label")
        score = 3 if labels else 0
        msg = "Direct labels present" if labels else "No direct labels detected"
        return {"score": score, "message": msg}

    def run_all(self, has_patterns=False, alt_palettes=None, chart_html=""):
        """Run all color accessibility checks and return comprehensive results.
        
        Args:
            has_patterns: Whether the chart uses patterns/shapes beyond color
            alt_palettes: List of alternative color palettes available
            chart_html: HTML content of the chart for analysis
            
        Returns:
            Dict containing all check results and summary with total score, 
            percentage, and letter grade
        """
        checks = {
            "palette_safety": self.check_palette_safety(),
            "background_contrast": self.check_background_contrast(),
            "adjacent_contrast": self.check_adjacent_contrast(),
            "grayscale_test": self.check_grayscale(),
            "pattern_encoding": self.check_pattern_encoding(has_patterns),
            "alt_theme": self.check_alt_theme(alt_palettes or []),
            "direct_labels": self.check_direct_labels(chart_html),
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 21  # 7 checks x 3
        pct = total / max_score * 100
        return {
            "checks": checks,
            "summary": {
                "total_score": total,
                "max_score": max_score,
                "percentage": round(pct, 1),
                "grade": grade(pct),
            },
        }


class ScreenReaderAccessibility:
    """Checks related to screen reader accessibility."""

    def __init__(self, chart_html):
        """Initialize ScreenReaderAccessibility with chart HTML.
        
        Args:
            chart_html: HTML content of the chart to analyze
        """
        self.html = chart_html
        self.soup = BeautifulSoup(chart_html, "html.parser")

    def has_alt_text(self):
        """Check for presence and quality of alt text and descriptions.
        
        Examines img alt attributes and desc elements to evaluate
        descriptive text quality based on average length.
        
        Returns:
            Dict with score (0-3) and quality message
        """
        img_alts = [img.get("alt", "").strip()
                    for img in self.soup.find_all("img")]
        descs = [d.get_text().strip() for d in self.soup.find_all("desc")]
        texts = [t for t in img_alts + descs if t]
        if not texts:
            return {"score": 0, "message": "No alt text or descriptions"}
        avg = sum(len(t) for t in texts) / len(texts)
        if avg >= 50:
            score, msg = 3, "Detailed descriptions"
        elif avg >= 20:
            score, msg = 2, "Basic descriptions"
        else:
            score, msg = 1, "Minimal descriptions"
        return {"score": score, "message": msg}

    def aria_roles(self):
        """Check for proper ARIA roles, labels, and descriptions.
        
        Evaluates the presence of semantic roles, aria-label attributes,
        and aria-describedby references for screen reader accessibility.
        
        Returns:
            Dict with score (0-3) and counts of each ARIA feature
        """
        roles = [tag["role"]
                 for tag in self.soup.find_all(attrs={"role": True})]
        labels = len(self.soup.find_all(attrs={"aria-label": True}))
        descby = len(self.soup.find_all(attrs={"aria-describedby": True}))
        score = min(3, sum(bool(x) for x in (roles, labels, descby)))
        return {"score": score, "roles": roles, "labels": labels, "describedby": descby}

    def semantic_table(self):
        """Check for proper semantic table structure and accessibility features.
        
        Evaluates presence of table headers, captions, and scope attributes
        for tabular data accessibility.
        
        Returns:
            Dict with score (0-3) and boolean flags for table features
        """
        tbl = self.soup.find("table")
        if not tbl:
            return {"score": 0, "message": "No data table"}
        has_th = bool(tbl.find("th"))
        has_cap = bool(tbl.find("caption") or tbl.find(scope=True))
        score = min(3, 1 + int(has_th) + int(has_cap))
        return {"score": score, "headers": has_th, "caption": has_cap}

    def heading_structure(self):
        """Check for proper heading hierarchy and structure.
        
        Evaluates heading elements (h1-h6) for logical sequence and
        proper nesting to support screen reader navigation.
        
        Returns:
            Dict with score (0-3) and list of heading levels found
        """
        hs = [int(h.name[1])
              for h in self.soup.find_all(re.compile(r"h[1-6]"))]
        if not hs:
            return {"score": 0, "message": "No headings"}
        seq = all(hs[i + 1] - hs[i] <= 1 for i in range(len(hs) - 1))
        score = 3 if seq and hs[0] == 1 else 2 if seq else 1
        return {"score": score, "levels": hs}

    def check_textual_equivalents(self):
        """Check for textual equivalents of chart elements.
        
        Looks for aria-labelledby attributes on axes and legend elements
        to ensure chart components have accessible text descriptions.
        
        Returns:
            Dict with score (0-3) and boolean flags for axes and legend
        """
        axes = bool(self.soup.select_one("g.axis[aria-labelledby]"))
        legend = bool(self.soup.select_one("g.legend[aria-labelledby]"))
        score = 3 if (axes and legend) else 1 if (axes or legend) else 0
        return {"score": score, "axes": axes, "legend": legend}

    def check_tabindex_order(self):
        """Check for logical tabindex ordering for keyboard navigation.
        
        Verifies that tabindex values are in ascending order to ensure
        predictable keyboard navigation flow.
        
        Returns:
            Dict with score (0 or 3) and list of tabindex values
        """
        tabs = [int(tag["tabindex"])
                for tag in self.soup.find_all(attrs={"tabindex": True})]
        seq = tabs == sorted(tabs) if tabs else False
        return {"score": 3 if seq else 0, "order": tabs}

    def run_all(self):
        """Run all screen reader accessibility checks and return comprehensive results.
        
        Returns:
            Dict containing all check results and summary with total score,
            percentage, and letter grade
        """
        checks = {
            "alt_text": self.has_alt_text(),
            "aria_roles": self.aria_roles(),
            "semantic_table": self.semantic_table(),
            "heading_structure": self.heading_structure(),
            "textual_equivalents": self.check_textual_equivalents(),
            "tabindex_order": self.check_tabindex_order(),
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 18  # 6 checks x 3
        pct = total / max_score * 100
        return {
            "checks": checks,
            "summary": {
                "total_score": total,
                "max_score": max_score,
                "percentage": round(pct, 1),
                "grade": grade(pct),
            },
        }


class CognitiveAccessibility:
    """Checks related to cognitive accessibility."""

    def __init__(self, elements):
        """Initialize CognitiveAccessibility with chart elements data.
        
        Args:
            elements: Dict containing chart element counts and properties
        """
        self.elements = elements or {}

    def element_count(self):
        """Evaluate cognitive load based on number of series and gridlines.
        
        Assesses whether the chart has an appropriate number of visual elements
        to avoid overwhelming users with cognitive disabilities.
        
        Returns:
            Dict with separate scores for series and gridlines, plus average score
        """
        s = self.elements.get("series", 0)
        g = self.elements.get("gridlines", 0)
        ss = 3 if s == 1 else 2 if s <= 12 else 1 if s <= 20 else 0
        gs = 3 if g <= 1 else 2 if g <= 3 else 1 if g <= 5 else 0
        return {"series_score": ss, "gridlines_score": gs, "score": (ss + gs) / 2}

    def legend_entries(self):
        """Evaluate cognitive load based on number of legend entries.
        
        Checks if the legend has an appropriate number of entries to
        avoid cognitive overload for users with disabilities.
        
        Returns:
            Dict with legend entry count and score (0-3)
        """
        c = self.elements.get("legend_entries", 0)
        sc = 3 if c <= 4 else 2 if c <= 6 else 1 if c <= 8 else 0
        return {"count": c, "score": sc}

    def encoding_complexity(self):
        """Evaluate complexity based on number of visual encodings used.
        
        Checks if the chart uses a reasonable number of visual encodings
        (color, size, shape, etc.) to maintain cognitive accessibility.
        
        Returns:
            Dict with encoding count and score (0 or 3)
        """
        e = self.elements.get("encodings", 0)
        sc = 3 if e <= 2 else 0
        return {"encodings": e, "score": sc}

    def labeling_clarity(self):
        """Evaluate clarity and understandability of chart labels.
        
        Checks for overly long labels or unclear abbreviations that could
        cause confusion for users with cognitive disabilities.
        
        Returns:
            Dict with total label count and score (0 or 3)
        """
        labels = self.elements.get("labels", [])
        # allow common abbreviations via whitelist
        whitelist = {"Q1", "Q2", "Q3", "Q4", "USD", "EUR"}
        unclear = any(
            len(lbl) > 20
            or (
                re.fullmatch(r"[A-Za-z]{1,3}", lbl)
                and lbl not in whitelist
            )
            for lbl in labels
        )
        return {"total_labels": len(labels), "score": 0 if unclear else 3}

    def check_visual_grouping(self, chart_html):
        """Check for visual grouping of related elements.
        
        Looks for grouping elements that help organize information
        and reduce cognitive load for users.
        
        Args:
            chart_html: HTML content to analyze for grouping elements
            
        Returns:
            Dict with score (0 or 3) and descriptive message
        """
        soup = BeautifulSoup(chart_html, "html.parser")
        grp = bool(soup.find(class_="group"))
        return {"score": 3 if grp else 0, "message": "Grouping" if grp else "No grouping"}

    def run_all(self):
        """Run all cognitive accessibility checks and return comprehensive results.
        
        Returns:
            Dict containing all check results and summary with total score,
            percentage, and letter grade
        """
        checks = {
            "element_count": self.element_count(),
            "legend_entries": self.legend_entries(),
            "max_encodings": self.encoding_complexity(),
            "labeling_clarity": self.labeling_clarity(),
            "visual_grouping": self.check_visual_grouping(self.elements.get("chart_html", "")),
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 15  # 5x3
        pct = total / max_score * 100
        return {
            "checks": checks,
            "summary": {
                "total_score": total,
                "max_score": max_score,
                "percentage": round(pct, 1),
                "grade": grade(pct),
            },
        }


class MotorAccessibility:
    """Checks related to motor and interaction accessibility."""

    def __init__(self, interactions):
        """Initialize MotorAccessibility with interaction data.
        
        Args:
            interactions: Dict containing interaction capabilities and properties
        """
        self.interactions = interactions or {}

    def keyboard_support(self):
        """Check if keyboard navigation is supported for chart interaction.
        
        Returns:
            Dict with score (0 or 3) and support status boolean
        """
        supported = bool(self.interactions.get("keyboard"))
        return {"score": 3 if supported else 0, "supported": supported}

    def hover_alternatives(self):
        """Check if alternatives to hover interactions are provided.
        
        Evaluates whether hover-only functionality has accessible alternatives
        for users who cannot use mouse hover.
        
        Returns:
            Dict with score (0 or 3) and support status boolean
        """
        supported = bool(self.interactions.get("hover_alternatives"))
        return {"score": 3 if supported else 0, "supported": supported}

    def touch_targets(self):
        """Evaluate touch target sizes for mobile accessibility.
        
        Checks if interactive elements meet minimum size requirements
        (44px) for users with motor impairments.
        
        Returns:
            Dict with target sizes, pass rate percentage, and score (0-3)
        """
        sizes = self.interactions.get("touch_targets", [])
        if not sizes:
            return {"sizes": sizes, "score": 0}
        rate = sum(1 for s in sizes if s >= 44) / len(sizes)
        score = 3 if rate >= 0.9 else 2 if rate >= 0.7 else 1 if rate >= 0.4 else 0
        return {"sizes": sizes, "pass_rate": round(rate * 100, 1), "score": score}

    def focus_indicators(self):
        """Check if visible focus indicators are provided for keyboard users.
        
        Returns:
            Dict with score (0 or 3) and support status boolean
        """
        supported = bool(self.interactions.get("focus_indicators"))
        return {"score": 3 if supported else 0, "supported": supported}

    def check_skip_links(self):
        """Check for skip links to help keyboard users navigate efficiently.
        
        Looks for skip navigation links that allow users to bypass
        repetitive content and jump to main chart content.
        
        Returns:
            Dict with score (0 or 3) and descriptive message
        """
        html = self.interactions.get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        skip = bool(
            soup.select_one(
                "a.skip, a[id*=skip], a[class*=skip-link], a[href^='#skip']"
            )
        )
        return {"score": 3 if skip else 0, "message": "Skip links present" if skip else "No skip links"}

    def run_all(self):
        """Run all motor accessibility checks and return comprehensive results.
        
        Returns:
            Dict containing all check results and summary with total score,
            percentage, and letter grade
        """
        checks = {
            "keyboard_support": self.keyboard_support(),
            "hover_alternatives": self.hover_alternatives(),
            "touch_targets": self.touch_targets(),
            "focus_indicators": self.focus_indicators(),
            "skip_links": self.check_skip_links(),
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 15
        pct = total / max_score * 100
        return {
            "checks": checks,
            "summary": {
                "total_score": total,
                "max_score": max_score,
                "percentage": round(pct, 1),
                "grade": grade(pct),
            },
        }


class ResponsiveAccessibility:
    """Checks related to responsive and scalable design."""

    def __init__(self, props):
        """Initialize ResponsiveAccessibility with responsive properties.
        
        Args:
            props: Dict containing responsive design capabilities and properties
        """
        self.props = props or {}

    def zoom_support(self):
        """Check if chart supports 200% zoom without horizontal scrolling.
        
        Returns:
            Dict with score (0 or 3) and support status boolean
        """
        supported = bool(self.props.get("zoom_200"))
        return {"score": 3 if supported else 0, "supported": supported}

    def responsive_layout(self):
        """Check if chart layout adapts to different screen sizes.
        
        Returns:
            Dict with score (0 or 3) and support status boolean
        """
        supported = bool(self.props.get("responsive"))
        return {"score": 3 if supported else 0, "supported": supported}

    def text_scaling(self):
        """Check if text can be scaled up without loss of functionality.
        
        Returns:
            Dict with score (0 or 3) and support status boolean
        """
        supported = bool(self.props.get("text_scaling"))
        return {"score": 3 if supported else 0, "supported": supported}

    def vector_graphics(self):
        """Check if chart uses scalable vector graphics (SVG).
        
        Vector graphics maintain quality at all zoom levels, improving
        accessibility for users who need to zoom content.
        
        Returns:
            Dict with score (0 or 3) and support status boolean
        """
        supported = bool(self.props.get("svg"))
        return {"score": 3 if supported else 0, "supported": supported}

    def mobile_variant(self):
        """Check if a mobile-optimized variant of the chart is available.
        
        Returns:
            Dict with score (0 or 3) and support status boolean
        """
        supported = bool(self.props.get("mobile_variant"))
        return {"score": 3 if supported else 0, "supported": supported}

    def check_zoom_tested(self):
        """Check if zoom functionality has been tested for accessibility.
        
        Returns:
            Dict with score (0 or 3) and testing status boolean
        """
        tested = bool(self.props.get("zoom_tested"))
        return {"score": 3 if tested else 0, "tested": tested}

    def check_font_scaling(self, chart_html):
        """Check if fonts use scalable units instead of fixed pixel sizes.
        
        Fixed pixel fonts don't scale with user preferences, reducing
        accessibility for users who need larger text.
        
        Args:
            chart_html: HTML content to analyze for font sizing
            
        Returns:
            Dict with score (0 or 3) and count of problematic pixel fonts
        """
        soup = BeautifulSoup(chart_html, "html.parser")
        inline_px = soup.find_all(style=re.compile(r"font-size:\s*\d+px"))
        return {"score": 0 if inline_px else 3, "px_found": len(inline_px)}

    def run_all(self):
        """Run all responsive accessibility checks and return comprehensive results.
        
        Returns:
            Dict containing all check results and summary with total score,
            percentage, and letter grade
        """
        checks = {
            "zoom_support": self.zoom_support(),
            "responsive_layout": self.responsive_layout(),
            "text_scaling": self.text_scaling(),
            "vector_graphics": self.vector_graphics(),
            "mobile_variant": self.mobile_variant(),
            "zoom_tested": self.check_zoom_tested(),
            "font_scaling": self.check_font_scaling(self.props.get("chart_html", "")),
        }
        total = sum(c["score"] for c in checks.values())
        max_score = 21
        pct = total / max_score * 100
        return {
            "checks": checks,
            "summary": {
                "total_score": total,
                "max_score": max_score,
                "percentage": round(pct, 1),
                "grade": grade(pct),
            },
        }
