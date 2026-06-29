import React, { useEffect, useRef } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import OSM from 'ol/source/OSM';
import { fromLonLat } from 'ol/proj';
import GeoJSONFormat from 'ol/format/GeoJSON';
import Feature from 'ol/Feature';
import LineString from 'ol/geom/LineString';
import Point from 'ol/geom/Point';
import Style from 'ol/style/Style';
import Stroke from 'ol/style/Stroke';
import Fill from 'ol/style/Fill';
import TextStyle from 'ol/style/Text';
import Draw from 'ol/interaction/Draw';

export default function MapView({
  polygon4326,
  parsedEdges,
  selectedEdgeIndex,
  drawMode,
  onEdgeSelect,
  onDrawComplete,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const parcelSourceRef = useRef(null);
  const edgeSourceRef = useRef(null);
  const edgeLayerRef = useRef(null);
  const drawInteractionRef = useRef(null);
  const selectedIdxRef = useRef(null);
  const onEdgeSelectRef = useRef(onEdgeSelect);
  const onDrawCompleteRef = useRef(onDrawComplete);

  useEffect(() => { onEdgeSelectRef.current = onEdgeSelect; }, [onEdgeSelect]);
  useEffect(() => { onDrawCompleteRef.current = onDrawComplete; }, [onDrawComplete]);

  // Initialise map once
  useEffect(() => {
    const parcelSource = new VectorSource();
    const edgeSource = new VectorSource();
    parcelSourceRef.current = parcelSource;
    edgeSourceRef.current = edgeSource;

    const parcelLayer = new VectorLayer({
      source: parcelSource,
      style: new Style({
        stroke: new Stroke({ color: '#2563eb', width: 2 }),
        fill: new Fill({ color: 'rgba(37,99,235,0.08)' }),
      }),
    });

    const edgeLayer = new VectorLayer({
      source: edgeSource,
      style: (feature) => {
        const idx = feature.get('edgeIndex');
        const isSelected = idx === selectedIdxRef.current;
        const isHovered = feature.get('hovered');
        const color = isSelected ? '#16a34a' : isHovered ? '#f59e0b' : '#94a3b8';
        const mid = new Point(feature.getGeometry().getCoordinateAt(0.5));

        return [
          new Style({
            stroke: new Stroke({ color, width: isSelected ? 4 : 3 }),
          }),
          new Style({
            geometry: mid,
            text: new TextStyle({
              text: `${idx}  (${feature.get('lengthFt')} ft)`,
              font: '11px sans-serif',
              fill: new Fill({ color: isSelected ? '#15803d' : '#334155' }),
              backgroundFill: new Fill({ color: 'rgba(255,255,255,0.85)' }),
              backgroundStroke: new Stroke({ color, width: 1 }),
              padding: [2, 4, 2, 4],
              offsetY: -10,
            }),
          }),
        ];
      },
    });
    edgeLayerRef.current = edgeLayer;

    const map = new Map({
      target: containerRef.current,
      layers: [
        new TileLayer({ source: new OSM() }),
        parcelLayer,
        edgeLayer,
      ],
      view: new View({
        center: fromLonLat([-98, 38]),
        zoom: 4,
      }),
    });
    mapRef.current = map;

    map.on('pointermove', (evt) => {
      const hit = map.forEachFeatureAtPixel(evt.pixel, (f) => f, {
        layerFilter: (l) => l === edgeLayer,
      });
      edgeSource.getFeatures().forEach((f) => f.set('hovered', f === hit, true));
      edgeLayer.changed();
      map.getTargetElement().style.cursor = hit ? 'pointer' : '';
    });

    map.on('click', (evt) => {
      const feature = map.forEachFeatureAtPixel(evt.pixel, (f) => f, {
        layerFilter: (l) => l === edgeLayer,
      });
      if (feature) onEdgeSelectRef.current(feature.get('edgeIndex'));
    });

    return () => map.setTarget(null);
  }, []);

  // Keep selected index ref in sync and refresh edge layer style
  useEffect(() => {
    selectedIdxRef.current = selectedEdgeIndex;
    edgeLayerRef.current?.changed();
  }, [selectedEdgeIndex]);

  // Redraw parcel and edges when polygon changes
  useEffect(() => {
    const parcelSource = parcelSourceRef.current;
    const edgeSource = edgeSourceRef.current;
    const map = mapRef.current;
    if (!parcelSource || !edgeSource || !map) return;

    parcelSource.clear();
    edgeSource.clear();
    if (!polygon4326) return;

    const format = new GeoJSONFormat();
    const parcelFeature = format.readFeature(polygon4326, {
      dataProjection: 'EPSG:4326',
      featureProjection: 'EPSG:3857',
    });
    parcelSource.addFeature(parcelFeature);
    map.getView().fit(parcelSource.getExtent(), { padding: [60, 60, 60, 60], duration: 500 });

    const ring = parcelFeature.getGeometry().getLinearRing(0).getCoordinates();
    parsedEdges.forEach(({ index, length_ft }) => {
      const start = ring[index];
      const end = ring[index + 1];
      if (!start || !end) return;
      const f = new Feature(new LineString([start, end]));
      f.set('edgeIndex', index);
      f.set('lengthFt', length_ft.toLocaleString());
      edgeSource.addFeature(f);
    });
  }, [polygon4326, parsedEdges]);

  // Add/remove draw interaction
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (drawMode) {
      const drawSource = new VectorSource();
      const interaction = new Draw({ source: drawSource, type: 'Polygon' });
      interaction.on('drawend', (evt) => {
        const geom = evt.feature.getGeometry().clone().transform('EPSG:3857', 'EPSG:4326');
        onDrawCompleteRef.current({ type: 'Polygon', coordinates: geom.getCoordinates() });
        map.removeInteraction(interaction);
        drawInteractionRef.current = null;
      });
      map.addInteraction(interaction);
      drawInteractionRef.current = interaction;
    } else {
      if (drawInteractionRef.current) {
        map.removeInteraction(drawInteractionRef.current);
        drawInteractionRef.current = null;
      }
    }
  }, [drawMode]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
}
