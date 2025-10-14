from colorsys import rgb_to_hls
import re


def grade(pct):
	if pct >= 90:
		return "A"
	if pct >= 80:
		return "B"
	if pct >= 70:
		return "C"
	if pct >= 60:
		return "D"
	return "F"
