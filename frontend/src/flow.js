import { useMemo, useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ReactFlow, Background, Controls, MiniMap } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import PersonNode from './PersonNode.js';
import FamilyJunctionNode from './FamilyJunctionNode.js';


function buildHighlightOverlayEdges(baseEdges, pathEdgeIds) {
  return (baseEdges ?? [])
    .filter((e) => pathEdgeIds.has(e.id))
    .filter((e) => {
      const isHiddenConnector =
        String(e.id).startsWith('hidden-') ||
        e?.style?.stroke === 'rgba(0,0,0,0)' ||
        e?.style?.strokeWidth === 0;
      return !isHiddenConnector;
    })
    .map((e) => ({
      ...e,
      id: `highlight-${e.id}`,
      animated: true,
      selectable: false,
      focusable: false,
      style: {
        ...(e.style || {}),
        stroke: '#f59e0b',
        strokeWidth: 5,
        strokeDasharray: '6 4',
        zIndex: 1000,
      },
    }));
}

function findPathBetweenNodes(nodes, edges, startId, endId) {
  const start = String(startId);
  const end = String(endId);

  if (start === end) {
    return {
      nodeIds: new Set([start]),
      edgeIds: new Set(),
    };
  }

  const adjacency = new Map();

  for (const node of nodes ?? []) {
    adjacency.set(String(node.id), []);
  }

  for (const edge of edges ?? []) {
    const source = String(edge.source);
    const target = String(edge.target);

    if (!adjacency.has(source)) adjacency.set(source, []);
    if (!adjacency.has(target)) adjacency.set(target, []);

    adjacency.get(source).push({ neighbor: target, edgeId: edge.id });
    adjacency.get(target).push({ neighbor: source, edgeId: edge.id });
  }

  const queue = [start];
  const visited = new Set([start]);
  const parent = new Map(); // child -> { prevNode, edgeId }

  while (queue.length > 0) {
    const current = queue.shift();
    if (current === end) break;

    for (const { neighbor, edgeId } of adjacency.get(current) ?? []) {
      if (visited.has(neighbor)) continue;

      visited.add(neighbor);
      parent.set(neighbor, { prevNode: current, edgeId });
      queue.push(neighbor);
    }
  }

  if (!visited.has(end)) {
    return {
      nodeIds: new Set(),
      edgeIds: new Set(),
    };
  }

  const nodeIds = new Set();
  const edgeIds = new Set();

  let current = end;
  nodeIds.add(current);

  while (current !== start) {
    const step = parent.get(current);
    if (!step) break;

    edgeIds.add(step.edgeId);
    current = step.prevNode;
    nodeIds.add(current);
  }

  return { nodeIds, edgeIds };
}

function Flow({ personId }) {
  const navigate = useNavigate();
  const [baseNodes, setBaseNodes] = useState([]);
  const [baseEdges, setBaseEdges] = useState([]);

  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Tree selection:
  const [trees, setTrees] = useState([]);
  const [selectedTreeId, setSelectedTreeId] = useState('');

  // Dismissible banner message:
  const [bannerMessage, setBannerMessage] = useState('');
  const [bannerTone, setBannerTone] = useState('info'); // 'info' | 'error'

  const [relPerson1, setRelPerson1] = useState('');
  const [relPerson2, setRelPerson2] = useState('');
  const [relationship, setRelationship] = useState('sibling');
  const [relResult, setRelResult] = useState(null);
  const [relLoading, setRelLoading] = useState(false);
  const [relError, setRelError] = useState(null);

  const [panelMode, setPanelMode] = useState('identify');
  const [searchRelationship, setSearchRelationship] = useState('sibling');
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);

  const [selected1, setSelected1] = useState(null);
  const [selected2, setSelected2] = useState(null);
  const [selected1Name, setSelected1Name] = useState(null);
  const [selected2Name, setSelected2Name] = useState(null);

  const [panelMinimized, setPanelMinimized] = useState(false);
  const [panelPos, setPanelPos] = useState({ x: 12, y: 12 });
  const dragRef = useRef({ dragging: false, startX: 0, startY: 0, origX: 0, origY: 0 });
  const bannerRef = useRef(null);

  const handlePanelDragStart = useCallback((e) => {
    dragRef.current = { dragging: true, startX: e.clientX, startY: e.clientY, origX: panelPos.x, origY: panelPos.y };
    e.preventDefault();
  }, [panelPos]);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (!dragRef.current.dragging) return;
      const minY = bannerRef.current ? bannerRef.current.getBoundingClientRect().bottom + 4 : 0;
      setPanelPos({
        x: dragRef.current.origX + (e.clientX - dragRef.current.startX),
        y: Math.max(minY, dragRef.current.origY + (e.clientY - dragRef.current.startY)),
      });
    };
    const onMouseUp = () => { dragRef.current.dragging = false; };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  const allowedRelationships = useMemo(
    () => [
      // Core
      'parent', 'mother', 'father',
      'child', 'son', 'daughter',
      'spouse', 'partner', 'husband', 'wife',
      // Siblings
      'sibling', 'full_sibling', 'half_sibling',
      'brother', 'sister', 'full_brother', 'half_brother', 'full_sister', 'half_sister',
      // Grandparents/children
      'grandparent', 'grandfather', 'grandmother',
      'grandchild', 'grandson', 'granddaughter',
      // Great-grandparents
      'great_grandparent', 'great_grandmother', 'great_grandfather',
      'great_great_grandparent', 'great_great_grandmother', 'great_great_grandfather',
      'great_great_great_grandparent',
      // Ancestors/descendants
      'ancestor', 'descendant',
      // Aunts/uncles/niblings
      'pibling', 'aunt', 'uncle',
      'grand_pibling', 'grand_aunt', 'grand_uncle',
      'great_grand_pibling', 'great_grand_aunt', 'great_grand_uncle',
      'niece', 'nephew', 'grand_niece', 'grand_nephew',
      // Cousins
      'cousin', 'first_cousin',
      'first_cousin_once_removed', 'first_cousin_twice_removed',
      'second_cousin', 'second_cousin_once_removed', 'second_cousin_twice_removed',
      'third_cousin', 'third_cousin_once_removed', 'third_cousin_twice_removed',
      // In-laws
      'parent_in_law', 'mother_in_law', 'father_in_law',
      'child_in_law', 'son_in_law', 'daughter_in_law',
      'sibling_in_law', 'brother_in_law', 'sister_in_law',
      // Step relations
      'step_parent', 'step_mother', 'step_father',
      'step_child', 'step_sibling', 'step_brother', 'step_sister',
    ],
    []
  );

  const nodeTypes = useMemo(
    () => ({
      person: PersonNode,
      familyJunction: FamilyJunctionNode,
    }),
    []
  );

  useEffect(() => {
    setRelPerson1(selected1 != null ? String(selected1) : '');
  }, [selected1]);

  useEffect(() => {
    setRelPerson2(selected2 != null ? String(selected2) : '');
  }, [selected2]);

  useEffect(() => {
    const basePersonStyle = {
      borderRadius: 8,
      border: '2px solid #333',
      padding: '10px',
    };

    const { nodeIds: pathNodeIds, edgeIds: pathEdgeIds } =
      selected1 != null && selected2 != null
        ? findPathBetweenNodes(baseNodes, baseEdges, selected1, selected2)
        : { nodeIds: new Set(), edgeIds: new Set() };


    setNodes(
      (baseNodes ?? []).map((n) => {
        const idStr = String(n.id);
        const idNum = parseInt(n.id, 10);

        if (n.type === 'person') {
          const isSelected1 = Number.isInteger(idNum) && idNum === selected1;
          const isSelected2 = Number.isInteger(idNum) && idNum === selected2;
          const isOnPath = pathNodeIds.has(idStr);

          const outline = isSelected1
            ? { outline: '4px solid #2563eb', outlineOffset: 2 }
            : isSelected2
              ? { outline: '4px solid #16a34a', outlineOffset: 2 }
              : isOnPath
                ? { outline: '4px solid #f59e0b', outlineOffset: 2 }
                : { outline: 'none' };

          return {
            ...n,
            style: {
              ...basePersonStyle,
              ...(n.style || {}),
              ...outline,
            },
          };
        }

        if (n.type === 'familyJunction') {
          const isOnPath = pathNodeIds.has(idStr);

          return {
            ...n,
            data: {
              ...(n.data || {}),
              isPathHighlighted: isOnPath,
            },
            style: {
              ...(n.style || {}),
            },
          };
        }

        return n;
      })
    );

    const overlayEdges = buildHighlightOverlayEdges(baseEdges, pathEdgeIds);

    setEdges([
      ...(baseEdges ?? []),
      ...overlayEdges,
    ]);
  }, [selected1, selected2, baseNodes, baseEdges]);

  function clearSelection() {
    setSelected1(null);
    setSelected2(null);
    setSelected1Name(null);
    setSelected2Name(null);
    setRelResult(null);
    setRelError(null);
  }

  function handleNodeClick(_evt, node) {
    if (node?.type !== 'person') return;

    const idNum = parseInt(node?.id, 10);
    if (!Number.isInteger(idNum)) return;

    const name = node?.data?.label ?? String(idNum);

    if (selected1 == null || (selected1 != null && selected2 != null)) {
      setSelected1(idNum);
      setSelected1Name(name);
      setSelected2(null);
      setSelected2Name(null);
      setRelResult(null);
      setRelError(null);
      return;
    }

    if (selected2 == null) {
      if (selected1 === idNum) {
        setSelected1(null);
        setSelected1Name(null);
      } else {
        setSelected2(idNum);
        setSelected2Name(name);
      }
    }
  }

  const runSearch = useCallback(async () => {
    setSearchError(null);
    setSearchResults(null);

    const p1 = parseInt(relPerson1, 10);
    if (!Number.isInteger(p1)) {
      setSearchError('Select a person by clicking a node first.');
      return;
    }

    const authKey = localStorage.getItem('key');
    if (!authKey) {
      setSearchError('Not logged in.');
      return;
    }

    setSearchLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/query/relationship/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-api-key': authKey },
        body: JSON.stringify({ person_id: p1, relationship: searchRelationship }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(data?.message || data?.description || response.statusText);
      }
      setSearchResults(data);
    } catch (e) {
      setSearchError(e?.message || String(e));
    } finally {
      setSearchLoading(false);
    }
  }, [relPerson1, searchRelationship]);

  function handleNodeDoubleClick(_evt, node) {
    if (node?.type !== 'person') return;
    const idNum = parseInt(node?.id, 10);
    if (!Number.isInteger(idNum)) return;
    navigate(`/person/${idNum}`);
  }

  async function runRelationshipQuery(mode = 'single') {
    setRelError(null);
    setRelResult(null);

    const p1 = parseInt(relPerson1, 10);
    const p2 = parseInt(relPerson2, 10);

    if (!Number.isInteger(p1) || !Number.isInteger(p2)) {
      setRelError('Select two people by clicking nodes (or type two valid IDs).');
      return;
    }

    const relToQuery = mode === 'all' ? 'all' : relationship;

    if (relToQuery !== 'all' && !allowedRelationships.includes(relToQuery)) {
      setRelError('Unsupported relationship.');
      return;
    }

    const authKey = localStorage.getItem('key');
    if (!authKey) {
      setRelError('Not logged in (missing auth key).');
      return;
    }

    setRelLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/query/relationship', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-api-key': authKey,
        },
        body: JSON.stringify({
          person1_id: p1,
          person2_id: p2,
          relationship: relToQuery,
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const msg = data?.message || data?.description || data?.error || response.statusText;
        throw new Error(msg);
      }

      setRelResult(data);
    } catch (e) {
      setRelError(e?.message || String(e));
    } finally {
      setRelLoading(false);
    }
  }

  useEffect(() => {
    const authKey = localStorage.getItem('key');
    if (!authKey) return;

    const fetchTrees = async () => {
      try {
        const resp = await fetch('http://127.0.0.1:5000/trees', {
          headers: { 'X-api-key': authKey },
        });

        const data = await resp.json().catch(() => null);
        if (!resp.ok) {
          const msg = data?.message || data?.description || resp.statusText;
          throw new Error(msg);
        }

        const list = data?.trees ?? [];
        setTrees(list);

        if (list.length === 0) {
          // User has no accessible trees. Show the banner instead of "failed to fetch".
          setBannerTone('info');
          setBannerMessage(
            "You don't have access to any trees yet. Ask a family group owner/editor to add you, or create a tree in one of your family groups."
          );
          setSelectedTreeId('');
          setBaseNodes([]);
          setBaseEdges([]);
          setNodes([]);
          setEdges([]);
          setLoading(false);
          return;
        }

        // Pick a default tree if none selected:
        if (!selectedTreeId && list.length > 0) {
          setSelectedTreeId(String(list[0].id));
        }
      } catch (e) {
        // Non-fatal: user may not belong to any groups/trees yet.
        setBannerTone('error');
        setBannerMessage(e?.message || 'Failed to load trees.');
        console.warn('Failed to fetch trees:', e);
      }
    };

    fetchTrees();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const fetchFamilyTree = async () => {
      try {
        setLoading(true);
        setError(null);

        const authKey = localStorage.getItem('key');
        if (!authKey) throw new Error('Not logged in.');

        if (!selectedTreeId) {
          // No trees available / selected
          setBaseNodes([]);
          setBaseEdges([]);
          setNodes([]);
          setEdges([]);
          return;
        }

        const response = await fetch(`http://127.0.0.1:5000/trees/${selectedTreeId}/view`, {
          headers: {
            'X-api-key': authKey,
          },
        });

        const data = await response.json().catch(() => null);
        if (!response.ok) {
          const msg = data?.message || data?.description || data?.error || response.statusText;
          throw new Error(msg);
        }

        // If backend provides an empty-tree message, show it as an info banner.
        if ((data?.nodes?.length ?? 0) === 0 && data?.message) {
          setBannerTone('info');
          setBannerMessage(String(data.message));
        }

        const basePersonStyle = {
          borderRadius: 8,
          border: '2px solid #333',
          padding: '10px',
        };

        const fetchedNodes = (data.nodes ?? []).map((n) => {
          if (n.type !== 'person') return n;

          return {
            ...n,
            style: {
              ...basePersonStyle,
              ...(n.style || {}),
            },
          };
        });

        const fetchedEdges = (data.edges ?? []).map((e, index) => ({
          ...e,
          id: e.id ?? `edge-${index}`,
        }));

        setBaseNodes(fetchedNodes);
        setBaseEdges(fetchedEdges);
        setNodes(fetchedNodes);
        setEdges(fetchedEdges);
      } catch (err) {
        setError(err.message);
        // Also show in banner (dismissible).
        setBannerTone('error');
        setBannerMessage(err?.message || 'Failed to load tree.');
      } finally {
        setLoading(false);
      }
    };

    fetchFamilyTree();
  }, [selectedTreeId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{ color: 'red' }}>Error: {error}</div>;

  const bannerStyles =
    bannerTone === 'error'
      ? { background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b' }
      : { background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1e40af' };

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {bannerMessage ? (
        <div
          ref={bannerRef}
          style={{
            position: 'absolute',
            top: 12,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 30,
            maxWidth: 760,
            width: 'calc(100% - 24px)',
            padding: '10px 12px',
            borderRadius: 10,
            boxShadow: '0 2px 12px rgba(0,0,0,0.10)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 10,
            ...bannerStyles,
          }}
          role="status"
          aria-live="polite"
        >
          <div style={{ flex: 1, fontSize: 13, lineHeight: 1.3 }}>{bannerMessage}</div>
          <button
            onClick={() => setBannerMessage('')}
            style={{
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              color: 'inherit',
              fontWeight: 800,
              fontSize: 16,
              lineHeight: 1,
              padding: '0 4px',
            }}
            aria-label="Dismiss message"
            title="Dismiss"
          >
            ×
          </button>
        </div>
      ) : null}

      <div
        style={{
          position: 'absolute',
          top: panelPos.y,
          left: panelPos.x,
          zIndex: 10,
          background: 'rgba(255,255,255,0.95)',
          border: '1px solid #ddd',
          borderRadius: 8,
          padding: 12,
          width: 340,
          boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        }}
      >
        <div
          onMouseDown={handlePanelDragStart}
          style={{ fontWeight: 700, marginBottom: panelMinimized ? 0 : 10, cursor: 'grab', display: 'flex', justifyContent: 'space-between', alignItems: 'center', userSelect: 'none' }}
        >
          <span>Tree Viewer</span>
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onClick={() => setPanelMinimized((m) => !m)}
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 14, padding: '0 4px', color: '#555', lineHeight: 1 }}
            title={panelMinimized ? 'Expand' : 'Minimize'}
          >
            {panelMinimized ? '▲' : '▼'}
          </button>
        </div>

        {!panelMinimized && (<>
        <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <select
            value={selectedTreeId}
            onChange={(e) => {
              setSelectedTreeId(e.target.value);
              // Clear stale banner when switching trees.
              setBannerMessage('');
            }}
            style={{ flex: 1, padding: 8 }}
          >
            {trees.length === 0 ? (
              <option value="">No accessible trees</option>
            ) : (
              trees.map((t) => (
                <option key={t.id} value={String(t.id)}>
                  {t.name}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Mode tabs */}
        <div style={{ display: 'flex', borderBottom: '2px solid #e5e7eb', marginBottom: 12 }}>
          {['identify', 'search'].map((mode) => (
            <button
              key={mode}
              onClick={() => { setPanelMode(mode); setRelResult(null); setRelError(null); setSearchResults(null); setSearchError(null); }}
              style={{
                flex: 1,
                padding: '6px 0',
                background: 'none',
                border: 'none',
                borderBottom: panelMode === mode ? '2px solid #2563eb' : '2px solid transparent',
                marginBottom: -2,
                fontWeight: panelMode === mode ? 700 : 400,
                color: panelMode === mode ? '#2563eb' : '#555',
                cursor: 'pointer',
                fontSize: 13,
                textTransform: 'capitalize',
              }}
            >
              {mode === 'identify' ? 'Identify' : 'Search'}
            </button>
          ))}
        </div>

        {/* Shared: person 1 selector + clear */}
        <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
          {panelMode === 'identify'
            ? 'Click two nodes to select (blue = Person 1, green = Person 2).'
            : 'Click one node to select a person, then choose a relationship.'}
        </div>

        <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <input
              type="text"
              value={relPerson1}
              onChange={(e) => setRelPerson1(e.target.value)}
              placeholder={panelMode === 'identify' ? 'Person 1 ID' : 'Person ID'}
              style={{ width: '100%', padding: '8px', border: '2px solid #2563eb', borderRadius: 4, fontSize: 13, boxSizing: 'border-box' }}
            />
            {selected1 != null && (
              <span
                onClick={() => { setSelected1(null); setSelected1Name(null); }}
                style={{ position: 'absolute', top: 8, right: 8, cursor: 'pointer', color: '#2563eb', fontWeight: 700 }}
              >&times;</span>
            )}
          </div>
          {panelMode === 'identify' && (
            <div style={{ flex: 1, position: 'relative' }}>
              <input
                type="text"
                value={relPerson2}
                onChange={(e) => setRelPerson2(e.target.value)}
                placeholder="Person 2 ID"
                style={{ width: '100%', padding: '8px', border: '2px solid #16a34a', borderRadius: 4, fontSize: 13, boxSizing: 'border-box' }}
              />
              {selected2 != null && (
                <span
                  onClick={() => { setSelected2(null); setSelected2Name(null); }}
                  style={{ position: 'absolute', top: 8, right: 8, cursor: 'pointer', color: '#16a34a', fontWeight: 700 }}
                >&times;</span>
              )}
            </div>
          )}
        </div>

        <button
          onClick={clearSelection}
          style={{ width: '100%', padding: 8, background: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5', borderRadius: 4, cursor: 'pointer', marginBottom: 10, fontSize: 12 }}
        >
          Clear Selection
        </button>

        {/* Identify mode */}
        {panelMode === 'identify' && (
          <>
            <select
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              style={{ width: '100%', padding: 8, marginBottom: 8, fontSize: 13 }}
            >
              {allowedRelationships.map((r) => (
                <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
              ))}
            </select>

            <div style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={() => runRelationshipQuery('single')}
                style={{ flex: 1, padding: 8, background: '#2563eb', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
              >
                Identify
              </button>
              <button
                onClick={() => runRelationshipQuery('all')}
                style={{ flex: 1, padding: 8, background: '#16a34a', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
              >
                Identify All
              </button>
            </div>

            {relLoading && <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>Loading…</div>}
            {relError && (
              <div style={{ marginTop: 8, color: '#c0392b', fontSize: 12, background: '#fdf0ef', padding: '6px 10px', borderRadius: 4 }}>{relError}</div>
            )}
            {relResult && relResult.exists !== undefined && (
              <div style={{
                marginTop: 8, padding: '8px 12px', borderRadius: 6,
                background: relResult.exists ? '#f0fdf4' : '#f8f8f8',
                border: `1px solid ${relResult.exists ? '#86efac' : '#e0e0e0'}`,
                fontSize: 13, color: relResult.exists ? '#166534' : '#666',
              }}>
                {relResult.exists
                  ? `✓ ${selected1Name ?? relResult.person1_id} IS the ${relResult.relationship.replace(/_/g, ' ')} of ${selected2Name ?? relResult.person2_id}`
                  : `${selected1Name ?? relResult.person1_id} is NOT the ${relResult.relationship.replace(/_/g, ' ')} of ${selected2Name ?? relResult.person2_id}`}
              </div>
            )}
            {relResult && relResult.true_relationships !== undefined && (
              <div style={{ marginTop: 8 }}>
                {relResult.true_relationships.length === 0 ? (
                  <div style={{ fontSize: 12, color: '#888', fontStyle: 'italic' }}>No relationships found.</div>
                ) : (
                  <>
                    <div style={{ fontSize: 11, color: '#555', marginBottom: 4 }}>
                      Relationships between <strong>{selected1Name ?? `#${relResult.person1_id}`}</strong> and <strong>{selected2Name ?? `#${relResult.person2_id}`}</strong>:
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxHeight: 140, overflowY: 'auto' }}>
                      {relResult.true_relationships.map((r) => (
                        <span key={r} style={{ padding: '2px 8px', borderRadius: 12, border: '1px solid #2563eb', color: '#2563eb', fontSize: 11, background: '#eff6ff', whiteSpace: 'nowrap' }}>
                          {r.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </>
        )}

        {/* Search mode */}
        {panelMode === 'search' && (
          <>
            <select
              value={searchRelationship}
              onChange={(e) => setSearchRelationship(e.target.value)}
              style={{ width: '100%', padding: 8, marginBottom: 8, fontSize: 13 }}
            >
              {allowedRelationships.map((r) => (
                <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>
              ))}
            </select>

            <button
              onClick={runSearch}
              style={{ width: '100%', padding: 8, background: '#7c3aed', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 12, marginBottom: 8 }}
            >
              Find All
            </button>

            {searchLoading && <div style={{ fontSize: 12, opacity: 0.7 }}>Loading…</div>}
            {searchError && (
              <div style={{ color: '#c0392b', fontSize: 12, background: '#fdf0ef', padding: '6px 10px', borderRadius: 4 }}>{searchError}</div>
            )}
            {searchResults && (
              <div>
                <div style={{ fontSize: 11, color: '#555', marginBottom: 4 }}>
                  {searchResults.results.length === 0
                    ? `No ${searchResults.relationship.replace(/_/g, ' ')} found for ${selected1Name ?? `#${searchResults.person_id}`}.`
                    : `${searchResults.results.length} ${searchResults.relationship.replace(/_/g, ' ')} of ${selected1Name ?? `#${searchResults.person_id}`}:`}
                </div>
                <div style={{ maxHeight: 180, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {searchResults.results.map((p) => {
                    const fullName = [p.firstName, p.middleName, p.lastName].filter(Boolean).join(' ');
                    return (
                      <Link
                        key={p.id}
                        to={`/person/${p.id}`}
                        style={{ padding: '6px 10px', background: '#f5f3ff', border: '1px solid #c4b5fd', borderRadius: 4, color: '#5b21b6', fontSize: 12, textDecoration: 'none' }}
                      >
                        {fullName}
                      </Link>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
        </>)}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        fitView
        nodeTypes={{ person: PersonNode, familyJunction: FamilyJunctionNode }}
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

export default Flow;