import { useEffect, useRef } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorSource from 'ol/source/Vector';
import OSM from 'ol/source/OSM';
import { fromLonLat } from 'ol/proj';
import Draw from 'ol/interaction/Draw';
import Modify from 'ol/interaction/Modify';
import Collection from 'ol/Collection';
import { useMapLayers } from '../hooks/useMapLayers';

export default function MapView({
  parcels,
  activeParcelId,
  activeParcel,
  selectedEdgeIndices,
  drawMode,
  onEdgeToggle,
  onDrawComplete,
  onActivateParcel,
  onParcelModified,
}) {
  const containerRef         = useRef(null);
  const mapRef               = useRef(null);
  const drawInteractionRef   = useRef(null);
  const modifyInteractionRef = useRef(null);
  const selectedIdxRef       = useRef([]);
  const activeIdRef          = useRef(null);
  const parcelFeaturesRef    = useRef(new Map()); // parcelId → OL Feature

  const onEdgeToggleRef     = useRef(onEdgeToggle);
  const onDrawCompleteRef   = useRef(onDrawComplete);
  const onActivateParcelRef = useRef(onActivateParcel);
  const onParcelModifiedRef = useRef(onParcelModified);

  useEffect(() => { onEdgeToggleRef.current     = onEdgeToggle; },     [onEdgeToggle]);
  useEffect(() => { onDrawCompleteRef.current   = onDrawComplete; },   [onDrawComplete]);
  useEffect(() => { onActivateParcelRef.current = onActivateParcel; }, [onActivateParcel]);
  useEffect(() => { onParcelModifiedRef.current = onParcelModified; }, [onParcelModified]);

  const {
    parcelLayerRef, edgeLayerRef, edgeSourceRef,
    addParcelToMap, removeParcelFromMap, updateEdges,
  } = useMapLayers(activeIdRef, selectedIdxRef);

  // Map lifecycle — runs once
  useEffect(() => {
    const edgeLayer   = edgeLayerRef.current;
    const edgeSource  = edgeSourceRef.current;
    const parcelLayer = parcelLayerRef.current;

    const map = new Map({
      target: containerRef.current,
      layers: [new TileLayer({ source: new OSM() }), parcelLayer, edgeLayer],
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
      const edgeFeature = map.forEachFeatureAtPixel(evt.pixel, (f) => f, {
        layerFilter: (l) => l === edgeLayer,
      });
      if (edgeFeature) {
        onEdgeToggleRef.current(edgeFeature.get('edgeIndex'));
        return;
      }
      const parcelFeature = map.forEachFeatureAtPixel(evt.pixel, (f) => f, {
        layerFilter: (l) => l === parcelLayer,
      });
      if (parcelFeature) onActivateParcelRef.current(parcelFeature.get('parcelId'));
    });

    return () => map.setTarget(null);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync selectedEdgeIndices ref
  useEffect(() => {
    selectedIdxRef.current = selectedEdgeIndices;
    edgeLayerRef.current?.changed();
  }, [selectedEdgeIndices]);

  // Sync parcel list to map (add/remove features); runs before active-parcel effect
  useEffect(() => {
    const currentIds = new Set(parcelFeaturesRef.current.keys());
    const nextIds    = new Set(parcels.map((p) => p.id));

    parcels.forEach((p) => {
      if (!currentIds.has(p.id)) {
        const feature = addParcelToMap(p.id, p.polygon4326);
        parcelFeaturesRef.current.set(p.id, feature);
      }
    });

    currentIds.forEach((id) => {
      if (!nextIds.has(id)) {
        removeParcelFromMap(id);
        parcelFeaturesRef.current.delete(id);
      }
    });
  }, [parcels]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync active parcel: update ref, fit map, manage Modify interaction
  useEffect(() => {
    activeIdRef.current = activeParcelId;
    parcelLayerRef.current?.changed();

    const map           = mapRef.current;
    const activeFeature = activeParcelId
      ? parcelFeaturesRef.current.get(activeParcelId)
      : null;

    if (activeFeature && map) {
      map.getView().fit(activeFeature.getGeometry().getExtent(), {
        padding: [60, 60, 60, 60], duration: 300, maxZoom: 19,
      });
    }

    if (modifyInteractionRef.current && map) {
      map.removeInteraction(modifyInteractionRef.current);
      modifyInteractionRef.current = null;
    }
    if (activeParcel?.source === 'draw' && activeFeature && map) {
      const collection = new Collection([activeFeature]);
      const modify     = new Modify({ features: collection });
      modify.on('modifyend', () => {
        const geom = activeFeature.getGeometry().clone().transform('EPSG:3857', 'EPSG:4326');
        onParcelModifiedRef.current({ type: 'Polygon', coordinates: geom.getCoordinates() });
      });
      map.addInteraction(modify);
      modifyInteractionRef.current = modify;
    }
  }, [activeParcelId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-sync edge layer when the active parcel's edges change (e.g. after shape edit + reparse)
  useEffect(() => {
    const activeFeature = activeParcelId
      ? parcelFeaturesRef.current.get(activeParcelId)
      : null;
    updateEdges(activeParcel?.edges ?? [], activeFeature);
  }, [activeParcel?.edges, activeParcelId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Draw interaction — stays active after each drawend for multi-draw
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (drawMode) {
      if (drawInteractionRef.current) return;
      const interaction = new Draw({ source: new VectorSource(), type: 'Polygon' });
      interaction.on('drawend', (evt) => {
        const geom = evt.feature.getGeometry().clone().transform('EPSG:3857', 'EPSG:4326');
        onDrawCompleteRef.current({ type: 'Polygon', coordinates: geom.getCoordinates() });
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
