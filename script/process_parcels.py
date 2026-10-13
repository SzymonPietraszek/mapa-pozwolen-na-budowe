import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict

import argparse
import pymupdf
import requests
from shapely import wkt
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parent
PDF_PATH = ROOT / "in" / "addresses.pdf"
OUTPUT_PATH = ROOT / "out" / "parcels.geojson"
REPORT_PATH = ROOT / "out" / "processing-report.json"

LAST_COLUMN = "Rodzaj decyzji"
LAST_COLUMN_END = (
    "umorzenie",
    "pozytywna",
    "prawa",
    "uchylenie",
    "negatywna",
    "odmowa",
    "wygaszenie",
)
COLUMNS = [
    "Nr decyzji",
    "Sygnatura sprawy",
    "Data wniosku",
    "Temat wniosku",
    "Adres inwestycji",
    "Lokalizacja",
    "Data decyzji",
    LAST_COLUMN,
]
COLUMN_LOCATIONS = {}

MAX_WORKERS = 20
REQUEST_TIMEOUT = 30

UNIT_CODES = {
    "Śródmieście": "126105_9",
    "Krowodrza": "126102_9",
    "Podgórze": "126104_9",
    "Nowa Huta": "126103_9",
}

LOCATION_PATTERN = re.compile(r"^obr\.\s*(\d+),\s*Nr dz\.\s*([^,]+),\s*j\.ew\.\s*(.+)$")


def download_pdf(url: str) -> Path:
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    PDF_PATH.write_bytes(response.content)

    print(f"Pobrano PDF: {PDF_PATH}")
    return PDF_PATH


def read_pdf() -> list[str]:
    data = []
    item = {}
    with pymupdf.open(PDF_PATH) as pdf:
        for page in pdf:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        text = span["text"].strip()
                        x = span["bbox"][0]

                        if not text or text == "Lp":
                            continue

                        if text in COLUMNS:
                            COLUMN_LOCATIONS[x] = text
                            continue

                        if x in COLUMN_LOCATIONS:
                            column_name = COLUMN_LOCATIONS[x].replace(" ", "_").lower()
                            item[column_name] = " ".join(
                                [item.get(column_name, ""), text]
                            ).strip()
                            if (
                                COLUMN_LOCATIONS[x] == LAST_COLUMN
                                and text in LAST_COLUMN_END
                            ):
                                data.append(item)
                                item = {}
    return data


def parse_location(location: str) -> dict:
    match = LOCATION_PATTERN.match(location)

    if not match:
        raise ValueError(f"Nieprawidłowa lokalizacja: {location}")

    obr, parcel_number, unit_name = match.groups()
    unit_name = unit_name.strip()
    parcel_number = parcel_number.strip()

    unit_code = UNIT_CODES.get(unit_name)

    if not unit_code:
        raise ValueError(f"Nieznana jednostka ewidencyjna: {unit_name}")

    uldk_id = f"{unit_code}.{obr.zfill(4)}.{parcel_number}"

    return {
        "location": location,
        "cadastral_unit": unit_name,
        "district_number": obr,
        "parcel_number": parcel_number,
        "uldk_id": uldk_id,
    }


def get_parcel(row: dict) -> list[dict]:
    features = []

    locations = [
        location.strip()
        for location in re.split(r"(?=obr\.)", row["lokalizacja"])
        if location.strip()
    ]

    for location in locations:
        properties = parse_location(location)
        uldk_id = properties["uldk_id"]

        response = requests.get(
            "https://uldk.gugik.gov.pl/",
            params={
                "request": "GetParcelById",
                "id": uldk_id,
                "result": "geom_wkt",
                "srid": "4326",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()

        text = response.text.strip()
        lines = text.splitlines()

        if not lines or lines[0].strip() != "0":
            raise ValueError(f"ULDK nie zwrócił działki {uldk_id}: {text}")

        if len(lines) < 2:
            raise ValueError(f"ULDK nie zwrócił geometrii dla {uldk_id}")

        geometry_text = re.sub(r"^SRID=\d+;", "", lines[1].strip())
        geometry = wkt.loads(geometry_text)

        if geometry.is_empty or not geometry.is_valid:
            raise ValueError(f"Nieprawidłowa geometria dla {uldk_id}")

        properties.update(
            {key: value for key, value in row.items() if key != "lokalizacja"}
        )

        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": mapping(geometry),
            }
        )

    return features


def main():
    parser = argparse.ArgumentParser(
        description="Pobiera PDF, odczytuje lokalizacje działek i generuje GeoJSON."
    )
    parser.add_argument("url", help="URL do pobrania pliku PDF")
    args = parser.parse_args()

    download_pdf(args.url)

    data = read_pdf()
    print(f"Znaleziono {len(data)} wpisów w PDF.")

    features = []
    errors = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_parcel, row): row for row in data}

        for future in as_completed(futures):
            row = futures[future]

            try:
                row_features = future.result()
                features.extend(row_features)

                for feature in row_features:
                    print(f"[OK] {feature['properties']['uldk_id']}")

            except Exception as error:
                errors.append(
                    {
                        "location": row.get("lokalizacja", ""),
                        "error": str(error),
                    }
                )
                print(f"[BŁĄD] {row.get('lokalizacja', '')}: {error}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    OUTPUT_PATH.write_text(
        json.dumps(feature_collection, ensure_ascii=False),
        encoding="utf-8",
    )

    report = {
        "pdf_url": args.url,
        "rows_found": len(data),
        "geometries_saved": len(features),
        "errors_count": len(errors),
        "errors": errors,
    }

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nZapisano geometrie: {len(features)}")
    print(f"Błędy: {len(errors)}")
    print(f"GeoJSON: {OUTPUT_PATH}")
    print(f"Raport: {REPORT_PATH}")


if __name__ == "__main__":
    main()
