import json
import argparse
from a11y_trees import (
    ColorAccessibility,
    ScreenReaderAccessibility,
    CognitiveAccessibility,
    MotorAccessibility,
    ResponsiveAccessibility
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run accessibility linter on data visualization config.")
    parser.add_argument("--config", type=str, required=True,
                        help="Path to the JSON configuration file.")
    parser.add_argument("--output", type=str,
                        help="Output file for report (optional)")
    parser.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format")
    return parser.parse_args()


def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_text_report(report, viz_name):
    """Print human-readable report."""
    print(f"\n{'='*70}")
    print(f"Accessibility Audit Report: {viz_name}")
    print(f"{'='*70}\n")

    pillars = [
        ("Color Accessibility", report["color_accessibility"]),
        ("Screen Reader Accessibility", report["screen_reader_accessibility"]),
        ("Cognitive Accessibility", report["cognitive_accessibility"]),
        ("Motor Accessibility", report["motor_accessibility"]),
        ("Responsive Accessibility", report["responsive_accessibility"])
    ]

    total_score = 0
    total_max = 0
    critical_failures = []

    for pillar_name, pillar_data in pillars:
        summary = pillar_data["summary"]
        print(
            f"{pillar_name}: {summary['total_score']}/{summary['max_score']} ({summary['percentage']:.0f}%) - Grade: {summary['grade']}")

        for check_name, check_data in pillar_data["checks"].items():
            status = "✓" if check_data["score"] >= 2 else "✗"
            print(
                f"  {status} {check_name}: {check_data['score']}/3 - {check_data.get('message', '')}")

            if check_data["score"] == 0:
                critical_failures.append(f"{pillar_name}: {check_name}")

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


def main():
    args = parse_args()
    cfg = load_config(args.config)

    # Run all accessibility checks
    report = {
        "viz_id": cfg.get("viz_id", "Unknown"),
        "viz_name": cfg.get("name", "Unnamed Visualization"),
        "color_accessibility": ColorAccessibility(
            cfg["palette"],
            cfg.get("background", "#ffffff")
        ).run_all(cfg.get("has_patterns", False), cfg.get("alt_palettes", []), cfg.get("chart_html", "")),

        "screen_reader_accessibility": ScreenReaderAccessibility(
            cfg.get("chart_html", "")
        ).run_all(),

        "cognitive_accessibility": CognitiveAccessibility(
            cfg.get("chart_elements", {})
        ).run_all(),

        "motor_accessibility": MotorAccessibility(
            cfg.get("interactions", {})
        ).run_all(),

        "responsive_accessibility": ResponsiveAccessibility(
            cfg.get("chart_props", {})
        ).run_all()
    }

    # Output report
    if args.format == "json":
        output = json.dumps(report, indent=2)
        print(output)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
    else:
        print_text_report(report, report["viz_name"])
        if args.output:
            # TODO: Implement text file output
            pass


if __name__ == "__main__":
    main()
