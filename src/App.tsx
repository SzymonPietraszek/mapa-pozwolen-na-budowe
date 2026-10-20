import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Map as MapLibreMap } from "maplibre-gl";
import maplibreWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Geometry } from "geojson";

maplibregl.setWorkerUrl(maplibreWorker);

type ParcelProperties = {
  adres_inwestycji?: string;
  data_decyzji?: string;
  data_wniosku?: string;
  nr_decyzji?: string;
  rodzaj_decyzji?: string;
  sygnatura_sprawy?: string;
  temat_wniosku?: string;
  location?: string;
  cadastral_unit?: string;
  district_number?: string;
  parcel_number?: string;
  uldk_id?: string;
};

type ParcelsGeoJSON = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: Geometry;
    properties: ParcelProperties;
  }>;
};

export default function App() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [parcels, setParcels] = useState<ParcelsGeoJSON | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadParcels() {
      try {
        const response = await fetch("/parcels.geojson", {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Błąd HTTP ${response.status}: /parcels.geojson`);
        }

        const data = (await response.json()) as ParcelsGeoJSON;

        if (
          data.type !== "FeatureCollection" ||
          !Array.isArray(data.features)
        ) {
          throw new Error("Nieprawidłowy format GeoJSON.");
        }

        setParcels(data);
      } catch (err) {
        console.error(err);
      }
    }

    void loadParcels();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: "https://tiles.openfreemap.org/styles/bright",
      center: [19.945, 50.049],
      zoom: 13,
    });

    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl());

    map.on("load", () => setMapLoaded(true));

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;

    if (!map || !mapLoaded || !parcels) return;

    const sourceId = "parcels";

    if (map.getSource(sourceId)) {
      (map.getSource(sourceId) as maplibregl.GeoJSONSource).setData(
        parcels as never,
      );
      return;
    }

    map.addSource(sourceId, {
      type: "geojson",
      data: parcels as never,
    });

    map.addLayer({
      id: "parcels-fill",
      type: "fill",
      source: sourceId,
      paint: {
        "fill-color": "#3388ff",
        "fill-opacity": 0.2,
      },
    });

    map.addLayer({
      id: "parcels-outline",
      type: "line",
      source: sourceId,
      paint: {
        "line-color": "#1763bb",
        "line-width": 1.5,
      },
    });

    map.on("click", "parcels-fill", (event) => {
      const feature = event.features?.[0];
      if (!feature) return;

      const properties = feature.properties ?? {};

      const content = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `Działka ${properties.parcel_number ?? ""}`;
      content.appendChild(title);

      for (const [label, value] of [
        ["Rodzaj decyzji", properties.rodzaj_decyzji],
        ["Temat wniosku", properties.temat_wniosku],
        ["Lokalizacja", properties.location],
        ["ID ULDK", properties.uldk_id],
        ["Data decyzji", properties.data_decyzji],
        ["Data wniosku", properties.data_wniosku],
        ["Nr decyzji", properties.nr_decyzji],
        ["Sygnatura sprawy", properties.sygnatura_sprawy],
        ["Adres inwestycji", properties.adres_inwestycji],
      ]) {
        if (value == null || value === "") continue;

        const row = document.createElement("div");
        row.textContent = `${label}: ${value}`;
        content.appendChild(row);
      }

      new maplibregl.Popup()
        .setLngLat(event.lngLat)
        .setDOMContent(content)
        .addTo(map);
    });

    map.on("mouseenter", "parcels-fill", () => {
      map.getCanvas().style.cursor = "pointer";
    });

    map.on("mouseleave", "parcels-fill", () => {
      map.getCanvas().style.cursor = "";
    });
  }, [mapLoaded, parcels]);

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100dvh",
      }}
    />
  );
}
