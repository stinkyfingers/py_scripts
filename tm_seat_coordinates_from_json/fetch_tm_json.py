#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "seat-mapping-3/1.0",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch Ticketmaster maps JSON for a project and write it to ./json/<project>.json."
    )
    parser.add_argument(
        "-p",
        "--project",
        required=True,
        type=int,
        help="Project ID used to resolve the maps.json URL and output file name.",
    )
    return parser.parse_args()


def load_project_url(maps_path, project):
    if not maps_path.exists():
        raise SystemExit(f"maps.json file not found: {maps_path}")

    with maps_path.open("r", encoding="utf-8") as handle:
        project_urls = json.load(handle)

    url = project_urls.get(str(project))
    if not url:
        raise SystemExit(f"No maps.json URL configured for project {project}")
    return url


def fetch_json(url):
    request = Request(url, headers=DEFAULT_HEADERS)
    try:
        with urlopen(request) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SystemExit(f"TM request failed with HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise SystemExit(f"TM request failed for {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"TM response from {url} was not valid JSON") from exc


def write_json(output_path, payload):
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main():
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    maps_path = script_dir / "maps.json"
    output_dir = script_dir / "json"
    output_dir.mkdir(parents=True, exist_ok=True)

    url = load_project_url(maps_path, args.project)
    payload = fetch_json(url)

    output_path = output_dir / f"{args.project}.json"
    write_json(output_path, payload)
    print(f"Wrote TM JSON to {output_path}")


if __name__ == "__main__":
    main()