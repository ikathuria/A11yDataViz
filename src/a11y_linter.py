import json
import argparse
import sys
import os

from a11y_trees import (
    ColorAccessibility,
    ScreenReaderAccessibility,
    CognitiveAccessibility,
    MotorAccessibility,
    ResponsiveAccessibility,
)

PILLARS = [
    ("Color Accessibility", "color_accessibility"),
    ("Screen Reader Accessibility", "screen_reader_accessibility"),
    ("Cognitive Accessibility", "cognitive_accessibility"),
    ("Motor Accessibility", "motor_accessibility"),
    ("Responsive Accessibility", "responsive_accessibility")
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run accessibility linter on data visualization config."
    )
    parser.add_argument("--config", type=str, required=True,
                        help="Path to the JSON configuration file.")
    parser.add_argument("--output", type=str,
                        help="Output file for report (optional)")
    parser.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format")
    parser.add_argument(
        "--pillars", type=str, nargs='*', help="Subset of pillars to run (e.g. color screen_reader)"
    )
    return parser.parse_args()


def load_config(path):
    if not os.path.exists(path):
        print(
            f"Error: Configuration file '{path}' not found.", file=sys.stderr)
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            sys.exit(1)


def print_text_report(report, viz_name):
    """Print human-readable report."""
    print(f"\n{'='*70}")
    print(f"Accessibility Audit Report: {viz_name}")
    print(f"{'='*70}\n")

    total_score = 0
    total_max = 0
    critical_failures = []

    for pillar_title, pillar_key in PILLARS:
        pillar_data = report[pillar_key]
        summary = pillar_data["summary"]
        print(
            f"{pillar_title}: {summary['total_score']}/{summary['max_score']} ({summary['percentage']:.0f}%) - Grade: {summary['grade']}"
        )

        for check_name, check_data in pillar_data["checks"].items():
            status = "✓" if check_data["score"] >= 2 else "✗"
            msg = check_data.get('message', '')
            details = f" - {msg}" if msg else ""
            print(
                f"  {status} {check_name}: {check_data['score']}/3{details}"
            )

            if check_data["score"] == 0:
                critical_failures.append(f"{pillar_title}: {check_name}")

        print()
        total_score += summary['total_score']
        total_max += summary['max_score']

    overall_pct = (total_score / total_max) * 100
    overall_rating = total_score / total_max * 3

    print(f"{'='*70}")
    print(f"OVERALL SCORE: {total_score}/{total_max} ({overall_pct:.1f}%)")
    print(f"RATING: {overall_rating:.2f}/3.00")
    print(f"{'='*70}\n")

    if critical_failures:
        print("CRITICAL FAILURES (Score 0):")
        for failure in critical_failures:
            print(f"  ✗ {failure}")
        print()


def run_checks(cfg, pillars_to_run=None):
    report = {
        "viz_id": cfg.get("viz_id", "Unknown"),
        "viz_name": cfg.get("name", "Unnamed Visualization")
    }
    pillar_funcs = {
        "color_accessibility": lambda: ColorAccessibility(
            cfg["palette"],
            cfg.get("background", "#ffffff")
        ).run_all(cfg.get("has_patterns", False), cfg.get("alt_palettes", []), cfg.get("chart_html", "")),
        "screen_reader_accessibility": lambda: ScreenReaderAccessibility(
            cfg.get("chart_html", "")
        ).run_all(),
        "cognitive_accessibility": lambda: CognitiveAccessibility(
            cfg.get("chart_elements", {})
        ).run_all(),
        "motor_accessibility": lambda: MotorAccessibility(
            cfg.get("interactions", {})
        ).run_all(),
        "responsive_accessibility": lambda: ResponsiveAccessibility(
            cfg.get("chart_props", {})
        ).run_all()
    }
    for pillartitle, pkey in PILLARS:
        if not pillars_to_run or pkey in pillars_to_run:
            try:
                report[pkey] = pillar_funcs[pkey]()
            except Exception as e:
                report[pkey] = {"summary": {"total_score": 0, "max_score": 0, "percentage": 0, "grade": "Error"},
                                "checks": {}, "error": str(e)}
                print(f"[ERROR] {pillartitle}: {e}", file=sys.stderr)
    return report


def main():
    args = parse_args()
    config = load_config(args.config)
    print(f"Running accessibility audit on: {args.config}\n")

    pillars_chosen = None
    if args.pillars:
        valid_keys = {p[1] for p in PILLARS}
        requested = set(args.pillars)
        unknown = requested - valid_keys
        if unknown:
            print(
                f"Unknown pillars requested: {', '.join(unknown)}", file=sys.stderr)
            sys.exit(1)
        pillars_chosen = requested

    report = run_checks(config, pillars_chosen)

    # Output
    if args.format == "json":
        output = json.dumps(report, indent=2)
        print(output)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Report written to {args.output}")
    else:
        print_text_report(report, report["viz_name"])
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                # Write plain text report to file as well
                orig_stdout = sys.stdout
                sys.stdout = f
                print_text_report(report, report["viz_name"])
                sys.stdout = orig_stdout
            print(f"Text report written to {args.output}")


if __name__ == "__main__":
    main()
