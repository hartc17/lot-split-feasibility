import { useState, useCallback } from 'react';

/**
 * Manages the collection of parcels in the workspace.
 *
 * Each parcel carries its own polygon, edges, edge selection, zoning form
 * values, and feasibility results. One parcel is "active" at a time; the
 * sidebar operates on the active parcel.
 *
 * @param {object} defaultZoningForm  Initial zoning form values for new parcels.
 *   Pass ZONING_DEFAULTS from ZoningPanel so new parcels start with sensible values.
 */
export function useParcels(defaultZoningForm) {
  const [parcels, setParcels] = useState([]);
  const [activeParcelId, setActiveParcelId] = useState(null);

  const add = useCallback((source, label, polygon4326, edges) => {
    const id = crypto.randomUUID();
    setParcels((prev) => [
      ...prev,
      {
        id,
        source,   // 'upload' | 'draw'
        label,
        polygon4326,
        edges,
        selectedEdgeIndices: [],
        zoningForm: { ...defaultZoningForm },
        results: null,
        loading: false,
        splitLines: [],         // [{id, geometry4326}] WGS84 GeoJSON LineStrings
        splitSections: null,    // ManualSplitEvaluation | null
        splitSectionsLoading: false,
      },
    ]);
    setActiveParcelId(id);
    return id;
  }, [defaultZoningForm]);

  const update = useCallback((id, patch) => {
    setParcels((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)));
  }, []);

  const remove = useCallback((id) => {
    setParcels((prev) => {
      const next = prev.filter((p) => p.id !== id);
      setActiveParcelId((current) => {
        if (current !== id) return current;
        return next.length > 0 ? next[next.length - 1].id : null;
      });
      return next;
    });
  }, []);

  const clearAll = useCallback(() => {
    setParcels([]);
    setActiveParcelId(null);
  }, []);

  const activeParcel = parcels.find((p) => p.id === activeParcelId) ?? null;

  return { parcels, activeParcelId, activeParcel, add, update, remove, clearAll, setActiveParcelId };
}
