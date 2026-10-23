import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pymupdf
import requests
from shapely import wkt
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parent
PDF_URLS = [
    "https://bip.krakow.pl/plik.php?zid=715390&wer=0&new=t&mode=shw",
    "https://bip.krakow.pl/plik.php?zid=662593&wer=0&new=t&mode=shw",
]
PDF_PATHS = [ROOT / "in" / "addresses2026.pdf", ROOT / "in" / "addresses2025.pdf"]
OUTPUT_PATH = ROOT.parent / "public" / "parcels.geojson"
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


def download_pdfs() -> Path:
    for url, pdf_path in zip(PDF_URLS, PDF_PATHS):
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(response.content)

        print(f"Pobrano PDF: {pdf_path}")


def read_pdfs() -> list[dict]:
    data = []
    item = {}
    for pdf_path in PDF_PATHS:
        with pymupdf.open(pdf_path) as pdf:
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
                                column_name = (
                                    COLUMN_LOCATIONS[x].replace(" ", "_").lower()
                                )
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


def process_data_locations(data: list[dict]) -> tuple[list[dict], list[dict]]:
    errors = []
    valid_data = []

    for row in data:
        if "lokalizacja" not in row:
            errors.append({"error": f"Brak lokalizacji w wierszu: {row}"})
            print(f"[BŁĄD] Brak lokalizacji w wierszu: {row}")
            continue

        row["lokalizacja"] = [
            item.strip()
            for item in re.split(r"(?=obr\.)", row["lokalizacja"])
            if item.strip()
        ]

        valid_data.append(row)

    return valid_data, errors


def get_uldk_id(location: str) -> dict:
    match = LOCATION_PATTERN.match(location)

    if not match:
        raise ValueError(f"Nieprawidłowa lokalizacja: {location}")

    obr, parcel_number, unit_name = match.groups()
    unit_name = unit_name.strip()
    parcel_number = parcel_number.strip()

    unit_code = UNIT_CODES.get(unit_name)

    if not unit_code:
        raise ValueError(f"Nieznana jednostka ewidencyjna: {unit_name}")

    return f"{unit_code}.{obr.zfill(4)}.{parcel_number}"


def get_parcel(location: str) -> dict:
    uldk_id = get_uldk_id(location)

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

    return {
        "uldk_id": uldk_id,
        "geometry": mapping(geometry),
    }


def get_geometries(data: list[dict]) -> dict[str, dict]:
    errors = []
    unique_locations = set()
    for row in data:
        unique_locations.update(row["lokalizacja"])

    geometries = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(get_parcel, location): location
            for location in unique_locations
        }

        for count, future in enumerate(as_completed(futures), start=1):
            location = futures[future]

            try:
                geometries[location] = {
                    "result": future.result(),
                    "error": None,
                }

                uldk_id = geometries[location]["result"]["uldk_id"]
                print(f"{count / len(unique_locations):3.0%} [OK] {uldk_id}")

            except Exception as error:
                geometries[location] = {
                    "result": None,
                    "error": str(error),
                }

                errors.append(
                    {
                        "location": location,
                        "error": str(error),
                    }
                )

                print(
                    f"{count / len(unique_locations):3.0%} [BŁĄD] {location}: {error}"
                )

    return geometries, errors


def create_geojson_features(data: list[dict], geometries: dict) -> dict:
    features = []
    for row in data:
        for location in row["lokalizacja"]:
            geometry_info = geometries.get(location)

            if not geometry_info or not geometry_info["result"]:
                continue

            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry_info["result"]["geometry"],
                    "properties": {
                        "uldk_id": geometry_info["result"]["uldk_id"],
                        **row,
                    },
                }
            )
    return features


def main():
    download_pdfs()

    data = read_pdfs()
    print(f"Znaleziono {len(data)} wpisów w PDF.")

    data, errors = process_data_locations(data)

    geometries, errors_from_geometries = get_geometries(data)
    errors.extend(errors_from_geometries)

    features = create_geojson_features(data, geometries)

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
        "pdf_urls": PDF_URLS,
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
