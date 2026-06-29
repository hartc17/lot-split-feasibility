/**
 * useMapLayers — creates and manages the OL vector layers for the map.
 *
 * Layer objects are built once via lazy ref initialization and returned as
 * stable refs, safe to pass directly into an OL Map's layers array. The
 * calling component is responsible for adding them to the map and for
 * updating sources when data changes.
 *
 * To add a new overlay layer (flood zones, utilities, etc.):
 *   1. Add its style config to MAP_LAYER_STYLES in config.js.
 *   2. Write a buildXLayer(source) function below following the same pattern.
 *   3. Initialize source + layer inside the lazy-init block and return them.
 */

import { useRef } from 'react';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import Style from 'ol/style/Style';
import Stroke from 'ol/style/Stroke';
import Fill from 'ol/style/Fill';
import TextStyle from 'ol/style/Text';
import Point from 'ol/geom/Point';
import { MAP_LAYER_STYLES as S } from '../config';

// ── Layer builders ────────────────────────────────────────────────────────────
// Plain functions, not hooks — buildable and testable independently of React.

function buildParcelLayer(source) {
  return new VectorLayer({
    source,
    style: new Style({
      stroke: new Stroke(S.parcel.stroke),
      fill:   new Fill(S.parcel.fill),
    }),
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

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * @param {React.MutableRefObject<number|null>} selectedIdxRef
 *   Ref that the edge layer's style function reads at render time.
 *   Must be the same ref object for the lifetime of the component.
 *
 * @returns {{
 *   parcelSourceRef: React.MutableRefObject<VectorSource>,
 *   edgeSourceRef:   React.MutableRefObject<VectorSource>,
 *   parcelLayerRef:  React.MutableRefObject<VectorLayer>,
 *   edgeLayerRef:    React.MutableRefObject<VectorLayer>,
 * }}
 */
export function useMapLayers(selectedIdxRef) {
  const parcelSourceRef = useRef(null);
  const edgeSourceRef   = useRef(null);
  const parcelLayerRef  = useRef(null);
  const edgeLayerRef    = useRef(null);

  // Lazy ref initialization: runs once even under React StrictMode's
  // double-invoke because the null check short-circuits on the second pass.
  if (parcelSourceRef.current === null) {
    const parcelSource = new VectorSource();
    const edgeSource   = new VectorSource();
    parcelSourceRef.current = parcelSource;
    edgeSourceRef.current   = edgeSource;
    parcelLayerRef.current  = buildParcelLayer(parcelSource);
    edgeLayerRef.current    = buildEdgeLayer(edgeSource, selectedIdxRef);
  }

  return { parcelSourceRef, edgeSourceRef, parcelLayerRef, edgeLayerRef };
}
