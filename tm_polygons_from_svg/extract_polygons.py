#!/usr/bin/env python3

import argparse
import csv
import os
import re
from html.parser import HTMLParser

COMMAND_RE = re.compile(r"[MmLlCcZz]|-?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?")


class PolygonsGroupParser(HTMLParser):
    """Collects <path> elements nested under <g class="polygons">."""

    def __init__(self):
        super().__init__()
        self.paths = []
        self._group_depth = 0
        self._polygons_group_depth = None

    def _enter_group(self, tag, attrs):
        if tag != "g":
            return
        self._group_depth += 1
        classes = dict(attrs).get("class", "").split()
        if self._polygons_group_depth is None and "polygons" in classes:
            self._polygons_group_depth = self._group_depth

    def _exit_group(self, tag):
        if tag != "g":
            return
        if self._group_depth == self._polygons_group_depth:
            self._polygons_group_depth = None
        self._group_depth -= 1

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self._enter_group(tag, attrs)
        if tag != "path" or self._polygons_group_depth is None:
            return
        attrs_dict = dict(attrs)
        path_data = attrs_dict.get("d")
        if not path_data:
            return
        self.paths.append(
            {
                "section_id": attrs_dict.get("data-section-id"),
                "data_section_name": attrs_dict.get("data-section-name"),
                "d": path_data,
            }
        )

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() == "g":
            self._exit_group("g")

    def handle_endtag(self, tag):
        self._exit_group(tag.lower())


def cubic_bezier_point(p0, p1, p2, p3, t):
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def parse_path_points(path_data, curve_steps=12):
    tokens = COMMAND_RE.findall(path_data)
    index = 0
    command = None
    current = (0.0, 0.0)
    subpath_start = None
    points = []

    def next_number():
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        token = tokens[index]
        if re.fullmatch(r"[MmLlCcZz]", token):
            command = token
            index += 1
        elif command is None:
            raise ValueError(f"Path data starts with a coordinate before any command: {path_data!r}")

        if command in ("M", "m"):
            x, y = next_number(), next_number()
            current = (current[0] + x, current[1] + y) if command == "m" else (x, y)
            subpath_start = current
            points.append(current)
            command = "l" if command == "m" else "L"
        elif command in ("L", "l"):
            x, y = next_number(), next_number()
            current = (current[0] + x, current[1] + y) if command == "l" else (x, y)
            points.append(current)
        elif command in ("C", "c"):
            x1, y1, x2, y2, x, y = (next_number() for _ in range(6))
            if command == "c":
                c1 = (current[0] + x1, current[1] + y1)
                c2 = (current[0] + x2, current[1] + y2)
                end = (current[0] + x, current[1] + y)
            else:
                c1, c2, end = (x1, y1), (x2, y2), (x, y)
            for step in range(1, curve_steps + 1):
                points.append(cubic_bezier_point(current, c1, c2, end, step / curve_steps))
            current = end
        elif command in ("Z", "z"):
            if subpath_start is not None:
                current = subpath_start
            command = None
        else:
            raise ValueError(f"Unsupported SVG path command {command!r} in {path_data!r}")

    return points


def extract_polygons(svg_path):
    parser = PolygonsGroupParser()
    with open(svg_path, "r", encoding="utf-8") as handle:
        parser.feed(handle.read())
    return parser.paths


def build_rows(paths):
    rows = []
    for path in paths:
        points = parse_path_points(path["d"])
        i = 0 # row order (order of points)
        for x, y in points:
            rows.append(
                {
                    "section_id": path["section_id"],
                    "section_code": path["data_section_name"],
                    "row_order": i,
                    "x": round(x, 2),
                    "y": round(y, 2),
                }
            )
            i += 1
    return rows


def write_csv(rows, output_path):
    fieldnames = ["section_id", "section_code", "row_order", "x", "y"]
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(description="Extract polygon points from an SVG's <g class=\"polygons\"> paths into a CSV.")
    parser.add_argument("--project", "-p", required=True, help="Project name; reads ./svgs/<project>.svg")
    return parser.parse_args()


def main():
    args = parse_args()
    svg_path = os.path.join("svgs", f"{args.project}.svg")
    output_path = os.path.join("polygons", f"{args.project}-polygons.csv")
    os.makedirs("polygons", exist_ok=True)
    paths = extract_polygons(svg_path)
    rows = build_rows(paths)
    write_csv(rows, output_path)
    print(f"Wrote {len(rows)} rows from {len(paths)} polygons to {output_path}")


if __name__ == "__main__":
    main()
