import csv
from collections import defaultdict

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from pathlib import Path

POLYGONS_CSV = Path(__file__).parent / "input_data" / "26-polygons.csv"
SEATS_CSV = Path(__file__).parent / "input_data" / "26-seat-coordinates.csv"


def load_polygons(path):
    sections = defaultdict(list)
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = sorted(reader, key=lambda r: (r["section_code"], int(r["row_order"])))
    for row in rows:
        sections[row["section_code"]].append((float(row["x"]), float(row["y"])))
    return sections


def load_seats(path):
    xs, ys = [], []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))
    return xs, ys


def main():
    sections = load_polygons(POLYGONS_CSV)
    seat_xs, seat_ys = load_seats(SEATS_CSV)

    fig, ax = plt.subplots(figsize=(10, 10))

    for points in sections.values():
        ax.add_patch(Polygon(points, closed=True, fill=False, edgecolor="steelblue"))

    ax.scatter(seat_xs, seat_ys, s=2, color="crimson")

    ax.set_aspect("equal")
    ax.autoscale()
    ax.set_title("Seat Map")
    plt.show()


if __name__ == "__main__":
    main()
