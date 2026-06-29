import { useEffect, useRef } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorSource from 'ol/source/Vector';
import OSM from 'ol/source/OSM';
import { fromLonLat } from 'ol/proj';
import GeoJSONFormat from 'ol/format/GeoJSON';
import Feature from 'ol/Feature';
import LineString from 'ol/geom/LineString';
import Draw from 'ol/interaction/Draw';
import { useMapLayers } from '../hooks/useMapLayers';

export default function MapView({
  polygon4326,
  parsedEdges,
  selectedEdgeIndices,
  drawMode,
  onEdgeToggle,
  onDrawComplete,
}) {
  const containerRef       = useRef(null);
  const mapRef             = useRef(null);
  const drawInteractionRef = useRef(null);
  const selectedIdxRef     = useRef([]);
  const onEdgeToggleRef    = useRef(onEdgeToggle);
  const onDrawCompleteRef  = useRef(onDrawComplete);

  useEffect(() => { onEdgeToggleRef.current   = onEdgeToggle;   }, [onEdgeToggle]);
  useEffect(() => { onDrawCompleteRef.current = onDrawComplete; }, [onDrawComplete]);

  const { parcelSourceRef, edgeSourceRef, parcelLayerRef, edgeLayerRef } =
    useMapLayers(selectedIdxRef);

  // ── Map lifecycle ───────────────────────────────────────────────────────────
  useEffect(() => {
    const edgeLayer  = edgeLayerRef.current;
    const edgeSource = edgeSourceRef.current;

    const map = new Map({
      target: containerRef.current,
      layers: [
        new TileLayer({ source: new OSM() }),
        parcelLayerRef.current,
        edgeLayer,
      ],
      view: new View({ center: fromLonLat([-98, 38]), zoom: 4 }),
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
      if (feature) onEdgeToggleRef.current(feature.get('edgeIndex'));
    });

    return () => map.setTarget(null);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Selected edges ──────────────────────────────────────────────────────────
  useEffect(() => {
    selectedIdxRef.current = selectedEdgeIndices;
    edgeLayerRef.current?.changed();
  }, [selectedEdgeIndices]);

  // ── Parcel + edge features ──────────────────────────────────────────────────
  useEffect(() => {
    const parcelSource = parcelSourceRef.current;
    const edgeSource   = edgeSourceRef.current;
    const map          = mapRef.current;
    if (!parcelSource || !edgeSource || !map) return;

    parcelSource.clear();
    edgeSource.clear();
    if (!polygon4326) return;

    const format        = new GeoJSONFormat();
    const parcelFeature = format.readFeature(polygon4326, {
      dataProjection:    'EPSG:4326',
      featureProjection: 'EPSG:3857',
    });
    parcelSource.addFeature(parcelFeature);
    map.getView().fit(parcelSource.getExtent(), { padding: [60, 60, 60, 60], duration: 500 });

    const ring = parcelFeature.getGeometry().getLinearRing(0).getCoordinates();
    parsedEdges.forEach(({ index, length_ft }) => {
      const start = ring[index];
      const end   = ring[index + 1];
      if (!start || !end) return;
      const f = new Feature(new LineString([start, end]));
      f.set('edgeIndex', index);
      f.set('lengthFt', length_ft.toLocaleString());
      edgeSource.addFeature(f);
    });
  }, [polygon4326, parsedEdges]);

  // ── Draw interaction ────────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (drawMode) {
      const interaction = new Draw({ source: new VectorSource(), type: 'Polygon' });
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
