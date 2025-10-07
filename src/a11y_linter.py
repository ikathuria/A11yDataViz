"""
Accessibility Linter for Data Visualization Configurations

Sample usage:
    python a11y_linter.py --config path/to/config.json

Sample config.json:
{
	"palette": [
		"#1f77b4",
		"#aec7e8",
		"#ff7f0e",
		"#2ca02c"
	],
	"background": "#ffffff",
	"chart_html": "<svg width=\"400\" height=\"200\" role=\"img\" aria-labelledby=\"title desc\"><title id=\"title\">Monthly Sales</title><desc id=\"desc\">Bar chart showing monthly sales from January to April</desc><rect x=\"10\" y=\"100\" width=\"50\" height=\"100\" fill=\"#1f77b4\"/><rect x=\"70\" y=\"80\" width=\"50\" height=\"120\" fill=\"#aec7e8\"/><rect x=\"130\" y=\"50\" width=\"50\" height=\"150\" fill=\"#ff7f0e\"/><rect x=\"190\" y=\"120\" width=\"50\" height=\"80\" fill=\"#2ca02c\"/></svg>",
	"chart_elements": {
		"series": 4,
		"gridlines": 5,
		"legend_entries": 4,
		"encodings": 3
	},
	"interactions": {
		"keyboard": true,
		"touch_targets": [
			50,
			50,
			50,
			50
		],
		"focus_indicators": true
	},
	"chart_props": {
		"zoom_200": true,
		"mobile_adaptive": true,
		"svg_scalable": true
	}
}

Sample output:
{
  "color_accessibility": {
    "palette_safety": {
      "safe": true,
      "message": "Colorblind-safe"
    },
    "background_contrast": [
      {
        "color": "#1f77b4",
        "ratio": 4.82,
        "pass": true
      },
      {
        "color": "#aec7e8",
        "ratio": 1.73,
        "pass": false
      },
      {
        "color": "#ff7f0e",
        "ratio": 2.53,
        "pass": false
      },
      {
        "color": "#2ca02c",
        "ratio": 3.4,
        "pass": false
      }
    ],
    "adjacent_contrast": [
      {
        "pair": [
          "#1f77b4",
          "#aec7e8"
        ],
        "ratio": 2.79,
        "pass": false
      },
      {
        "pair": [
          "#aec7e8",
          "#ff7f0e"
        ],
        "ratio": 1.46,
        "pass": false
      },
      {
        "pair": [
          "#ff7f0e",
          "#2ca02c"
        ],
        "ratio": 1.34,
        "pass": false
      }
    ],
    "grayscale_test": {
      "unique": true,
      "luminances": [
        0.17,
        0.56,
        0.36,
        0.26
      ]
    }
  },
  "screen_reader_accessibility": {
    "alt_text": {
      "has_img_alt": false,
      "has_desc": false
    },
    "aria_roles": {
      "roles": [
        "img"
      ]
    },
    "semantic_table": {
      "has_table": false,
      "has_th": false
    }
  },
  "cognitive_accessibility": {
    "element_count": {
      "series": 4,
      "gridlines": 5
    },
    "legend_entries": {
      "legend_entries": 4,
      "pass": true
    },
    "layout_complexity": {
      "encodings": 3,
      "pass": true
    }
  },
  "motor_accessibility": {
    "keyboard_support": {
      "keyboard": true
    },
    "touch_targets": {
      "touch_sizes": [
        50,
        50,
        50,
        50
      ],
      "pass": true
    },
    "focus_indicators": {
      "focus_indicators": true
    }
  },
  "responsive_accessibility": {
    "zoom_behavior": {
      "zoom_200": true
    },
    "mobile_layout": {
      "mobile_adaptive": true
    },
    "svg_scalable": {
      "svg_scalable": true
    }
  }
}
"""

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
    parser = argparse.ArgumentParser(description="Run accessibility linter on data visualization config.")
    parser.add_argument("--config", type=str, help="Path to the JSON configuration file.")
    return parser.parse_args()


def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main(config_path):
    cfg = load_config(config_path)
    report = {
        "color_accessibility": ColorAccessibility(cfg["palette"], cfg.get("background")).run_all(),
        "screen_reader_accessibility": ScreenReaderAccessibility(cfg.get("chart_html", "")).run_all(),
        "cognitive_accessibility": CognitiveAccessibility(cfg.get("chart_elements", {})).run_all(),
        "motor_accessibility": MotorAccessibility(cfg.get("interactions", {})).run_all(),
        "responsive_accessibility": ResponsiveAccessibility(cfg.get("chart_props", {})).run_all()
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    args = parse_args()
    main(args.config)

