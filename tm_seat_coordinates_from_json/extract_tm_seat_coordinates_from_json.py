#!/usr/bin/env python3

import argparse
import csv
import json
import re
from pathlib import Path


OUTPUT_FIELDNAMES = [
    "section_code",
    "row_level",
    "seat_nubmer",
    "x",
    "y",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract Ticketmaster seat coordinates from ./json/<project>.json into a CSV."
    )
    parser.add_argument(
        "-p",
        "--project",
        required=True,
        type=int,
        help="Project ID used to read ./json/<project>.json.",
    )
    return parser.parse_args()


def load_json_payload(input_path):
    raw_text = input_path.read_text(encoding="utf-8")
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        sanitized_text = re.sub(r"([}\]])\s*,\s*[A-Za-z_][A-Za-z0-9_]*\s*(?=[{\[])", r"\1,", raw_text)
        return json.loads(sanitized_text)


def append_seat_rows(node, output_rows, current_section=None, current_row=None):
    if isinstance(node, dict):
        segment_category = node.get("segmentCategory")
        if segment_category == "SECTION":
            current_section = node.get("name")
        elif segment_category == "ROW":
            current_row = node.get("name")
            places = node.get("placesNoKeys") or []
            for place in places:
                if not isinstance(place, list) or len(place) < 4:
                    continue
                seat_number = place[1]
                x_coordinate = place[2]
                y_coordinate = place[3]
                output_rows.append(
                    {
                        "section": "" if current_section is None else str(current_section),
                        "row": "" if current_row is None else str(current_row),
                        "seat": "" if seat_number is None else str(seat_number),
                        "x": "" if x_coordinate is None else str(x_coordinate),
                        "y": "" if y_coordinate is None else str(y_coordinate),
                    }
                )

        for value in node.values():
            append_seat_rows(value, output_rows, current_section, current_row)
        return

    if isinstance(node, list):
        for item in node:
            append_seat_rows(item, output_rows, current_section, current_row)


def extract_seat_rows(json_payload):
    output_rows = []
    append_seat_rows(json_payload, output_rows)
    return output_rows


def write_csv(output_path, rows, fieldnames=OUTPUT_FIELDNAMES):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def filter_seat_sections(rows):
    sections = []
    vals = list({item["section"] for item in rows})
    for v in vals:
        sections.append({ "section": v })
    return sorted(sections, key=lambda x: x["section"])


def main():
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    input_path = script_dir / "json" / f"{args.project}.json"
    output_path = script_dir / "tm_seat_coordinates" / f"{args.project}-seat-coordinates.csv"
    section_output_path = script_dir / "tm_seat_coordinates" / f"{args.project}-seat-sections.csv"

    if not input_path.exists():
        raise SystemExit(f"Input JSON not found: {input_path}")

    json_payload = load_json_payload(input_path)
    output_rows = extract_seat_rows(json_payload)
    write_csv(output_path, output_rows)

    write_csv(section_output_path, filter_seat_sections(output_rows), ["section"])

    print(f"Wrote {len(output_rows)} seat coordinate rows to {output_path}")


if __name__ == "__main__":
    main()