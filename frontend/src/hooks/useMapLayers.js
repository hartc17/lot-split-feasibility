import { useRef, useCallback } from 'react';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import Style from 'ol/style/Style';
import Stroke from 'ol/style/Stroke';
import Fill from 'ol/style/Fill';
import TextStyle from 'ol/style/Text';
import Point from 'ol/geom/Point';
import Feature from 'ol/Feature';
import LineString from 'ol/geom/LineString';
import GeoJSONFormat from 'ol/format/GeoJSON';
import { MAP_LAYER_STYLES as S } from '../config';

const _fmt = new GeoJSONFormat();

// ── Layer builders ────────────────────────────────────────────────────────────

function buildParcelLayer(source, activeIdRef) {
  return new VectorLayer({
    source,
    style: (feature) => {
      const cfg = feature.get('parcelId') === activeIdRef.current
        ? S.parcel.active
        : S.parcel.inactive;
      return new Style({
        stroke: new Stroke(cfg.stroke),
        fill:   new Fill(cfg.fill),
      });
    },
  });
}

function buildEdgeLayer(source, selectedIdxRef) {
  return new VectorLayer({
    source,
    style: (feature) => {
      const idx        = feature.get('edgeIndex');
      const isSelected = selectedIdxRef.current?.includes(idx);
      const isHovered  = feature.get('hovered');
      const stroke     = isSelected ? S.edge.selected : isHovered ? S.edge.hovered : S.edge.default;
      const lbl        = S.edge.label;

      return [
        new Style({ stroke: new Stroke(stroke) }),
        new Style({
          geometry: new Point(feature.getGeometry().getCoordinateAt(0.5)),
          text: new TextStyle({
            text:              `${idx}  (${feature.get('lengthFt')} ft)`,
            font:              lbl.font,
            fill:              new Fill({ color: isSelected ? lbl.selectedColor : lbl.defaultColor }),
            backgroundFill:   new Fill({ color: lbl.bgFill }),
            backgroundStroke: new Stroke({ color: stroke.color, width: 1 }),
            padding:          lbl.padding,
            offsetY:          lbl.offsetY,
          }),
        }),
      ];
    },
  });
}

function buildSplitLineLayer(source) {
  return new VectorLayer({
    source,
    style: new Style({
      stroke: new Stroke({
        color:    S.splitLine.color,
        width:    S.splitLine.width,
        lineDash: S.splitLine.lineDash,
      }),
    }),
    zIndex: 10,
  });
}

function buildSplitSectionLayer(source) {
  return new VectorLayer({
    source,
    style: (feature) => {
      const cfg = feature.get('viable') ? S.splitSection.viable : S.splitSection.notViable;
      return new Style({
        stroke: new Stroke(cfg.stroke),
        fill:   new Fill(cfg.fill),
      });
    },
    zIndex: 5,
  });
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useMapLayers(activeIdRef, selectedIdxRef) {
  const parcelSourceRef       = useRef(null);
  const edgeSourceRef         = useRef(null);
  const parcelLayerRef        = useRef(null);
  const edgeLayerRef          = useRef(null);
  const splitLineSourceRef    = useRef(null);
  const splitLineLayerRef     = useRef(null);
  const splitSectionSourceRef = useRef(null);
  const splitSectionLayerRef  = useRef(null);

  if (parcelSourceRef.current === null) {
    const parcelSource       = new VectorSource();
    const edgeSource         = new VectorSource();
    const splitLineSource    = new VectorSource();
    const splitSectionSource = new VectorSource();
    parcelSourceRef.current       = parcelSource;
    edgeSourceRef.current         = edgeSource;
    splitLineSourceRef.current    = splitLineSource;
    splitSectionSourceRef.current = splitSectionSource;
    parcelLayerRef.current        = buildParcelLayer(parcelSource, activeIdRef);
    edgeLayerRef.current          = buildEdgeLayer(edgeSource, selectedIdxRef);
    splitLineLayerRef.current     = buildSplitLineLayer(splitLineSource);
    splitSectionLayerRef.current  = buildSplitSectionLayer(splitSectionSource);
  }

  const addParcelToMap = useCallback((id, polygon4326) => {
    const format  = new GeoJSONFormat();
    const feature = format.readFeature(polygon4326, {
      dataProjection:    'EPSG:4326',
      featureProjection: 'EPSG:3857',
    });
    feature.set('parcelId', id);
    parcelSourceRef.current.addFeature(feature);
    parcelLayerRef.current.changed();
    return feature;
  }, []);

  const removeParcelFromMap = useCallback((id) => {
    const feature = parcelSourceRef.current
      .getFeatures()
      .find((f) => f.get('parcelId') === id);
    if (feature) parcelSourceRef.current.removeFeature(feature);
  }, []);

  const updateEdges = useCallback((edges, activeParcelFeature) => {
    const edgeSource = edgeSourceRef.current;
    edgeSource.clear();
    if (!activeParcelFeature || !edges.length) return;
    const ring = activeParcelFeature.getGeometry().getLinearRing(0).getCoordinates();
    edges.forEach(({ index, length_ft }) => {
      const start = ring[index];
      const end   = ring[index + 1];
      if (!start || !end) return;
      const f = new Feature(new LineString([start, end]));
      f.set('edgeIndex', index);
      f.set('lengthFt', length_ft.toLocaleString());
      edgeSource.addFeature(f);
    });
  }, []);

  const updateSplitLines = useCallback((splitLines) => {
    const source = splitLineSourceRef.current;
    source.clear();
    splitLines.forEach(({ id, geometry4326 }) => {
      const feature = _fmt.readFeature(geometry4326, {
        dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857',
      });
      feature.set('splitLineId', id);
      source.addFeature(feature);
    });
  }, []);

  const updateSplitSections = useCallback((splitSections) => {
    const source = splitSectionSourceRef.current;
    source.clear();
    if (!splitSections) return;
    splitSections.sections.forEach((section, i) => {
      const feature = _fmt.readFeature(section.geometry, {
        dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857',
      });
      const viable = (
        section.meets_min_lot_size &&
        section.meets_min_frontage &&
        section.has_buildable_envelope
      );
      feature.set('sectionIndex', i);
      feature.set('viable', viable);
      source.addFeature(feature);
    });
  }, []);

  return {
    parcelSourceRef, edgeSourceRef, parcelLayerRef, edgeLayerRef,
    splitLineLayerRef, splitSectionLayerRef,
    addParcelToMap, removeParcelFromMap, updateEdges,
    updateSplitLines, updateSplitSections,
  };
}
