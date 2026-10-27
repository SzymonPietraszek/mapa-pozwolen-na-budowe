import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Map as MapLibreMap } from "maplibre-gl";
import maplibreWorker from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import type { FeatureCollection, Geometry } from "geojson";
import { parcelFillColor } from "./mapStyles";

maplibregl.setWorkerUrl(maplibreWorker);

type ParcelsGeoJSON = FeatureCollection<Geometry, Record<string, unknown>>;

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
        "fill-color": parcelFillColor,
        "fill-opacity": 0.5,
      },
    });

    map.addLayer({
      id: "parcels-outline",
      type: "line",
      source: sourceId,
      paint: {
        "line-color": [
          "case",
          ["in", "jednorodzi", ["get", "temat_wniosku"]],
          "#16a34a", // Jednorodzinna — zielony
          ["in", "wielorodzi", ["get", "temat_wniosku"]],
          "#dc2626", // Wielorodzinna — czerwony
          "#1763bb", // Pozostałe — niebieski
        ],
        "line-width": 1.5,
      },
    });

    map.on("click", "parcels-fill", (event) => {
      const feature = event.features?.[0];
      if (!feature) return;

      const properties = feature.properties ?? {};
      const content = document.createElement("div");

      for (const [key, value] of Object.entries(properties)) {
        if (value == null || value === "") continue;

        const label = key.replaceAll("_", " ");
        const row = document.createElement("div");
        const labelElement = document.createElement("strong");

        labelElement.textContent = `${label}: `;
        row.appendChild(labelElement);
        row.appendChild(document.createTextNode(String(value)));

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
