import { useMemo, useState, useEffect } from 'react';
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
  const [baseNodes, setBaseNodes] = useState([]);
  const [baseEdges, setBaseEdges] = useState([]);

  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [relPerson1, setRelPerson1] = useState('');
  const [relPerson2, setRelPerson2] = useState('');
  const [relationship, setRelationship] = useState('sibling');
  const [relResult, setRelResult] = useState(null);
  const [relLoading, setRelLoading] = useState(false);
  const [relError, setRelError] = useState(null);

  const [selected1, setSelected1] = useState(null);
  const [selected2, setSelected2] = useState(null);

  const allowedRelationships = useMemo(
    () => [
      'parent',
      'spouse',
      'sibling',
      'brother',
      'sister',
      'grandparent',
      'grandfather',
      'grandmother',
      'child',
      'son',
      'daughter',
      'ancestor',
      'descendant',
      'cousin',
      'aunt',
      'uncle',
      'niece',
      'nephew',
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
    setRelResult(null);
    setRelError(null);
  }

  function handleNodeClick(_evt, node) {
    if (node?.type !== 'person') return;

    const idNum = parseInt(node?.id, 10);
    if (!Number.isInteger(idNum)) return;

    if (selected1 == null || (selected1 != null && selected2 != null)) {
      setSelected1(idNum);
      setSelected2(null);
      setRelResult(null);
      setRelError(null);
      return;
    }

    if (selected2 == null) {
      if (selected1 === idNum) {
        setSelected1(null);
      } else {
        setSelected2(idNum);
      }
    }
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
    const fetchFamilyTree = async () => {
      try {
        setLoading(true);
        setError(null);

        const authKey = localStorage.getItem('key');
        const response = await fetch(`http://127.0.0.1:5000/tree/${personId}`, {
          headers: {
            'X-api-key': authKey,
          }
        });

        if (!response.ok) throw new Error('Failed to fetch tree.');

        const data = await response.json();

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
      } finally {
        setLoading(false);
      }
    };

    if (personId) fetchFamilyTree();
  }, [personId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{ color: 'red' }}>Error: {error}</div>;

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      <div
        style={{
          position: 'absolute',
          top: 12,
          left: 12,
          zIndex: 10,
          background: 'rgba(255,255,255,0.95)',
          border: '1px solid #ddd',
          borderRadius: 8,
          padding: 12,
          width: 340,
          boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: 6 }}>Relationship Query</div>
        <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 10 }}>
          Click two people in the tree to select them (blue = Person 1, green = Person 2).
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input
            value={relPerson1}
            onChange={(e) => setRelPerson1(e.target.value)}
            placeholder="Person 1 ID"
            style={{ flex: 1, padding: 8 }}
          />
          <input
            value={relPerson2}
            onChange={(e) => setRelPerson2(e.target.value)}
            placeholder="Person 2 ID"
            style={{ flex: 1, padding: 8 }}
          />
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <select
            value={relationship}
            onChange={(e) => setRelationship(e.target.value)}
            style={{ flex: 1, padding: 8 }}
          >
            {allowedRelationships.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>

          <button
            onClick={() => runRelationshipQuery('single')}
            disabled={relLoading}
            style={{ padding: '8px 12px' }}
          >
            {relLoading ? 'Querying…' : 'Query'}
          </button>

          <button
            onClick={() => runRelationshipQuery('all')}
            disabled={relLoading}
            style={{ padding: '8px 12px' }}
            title="Infer all true relationships"
          >
            Infer
          </button>

          <button
            onClick={clearSelection}
            disabled={relLoading}
            style={{ padding: '8px 12px' }}
          >
            Clear
          </button>
        </div>

        {relError ? (
          <div style={{ color: 'crimson', fontSize: 13 }}>{relError}</div>
        ) : null}

        {relResult ? (
          <div style={{ fontSize: 13, marginTop: 6 }}>
            {Array.isArray(relResult.true_relationships) ? (
              <div>
                <div style={{ marginBottom: 6 }}>
                  <strong>True relationships</strong> ({relResult.true_relationships.length})
                </div>
                {relResult.true_relationships.length ? (
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    {relResult.true_relationships.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                ) : (
                  <div>None found.</div>
                )}
              </div>
            ) : (
              <div>
                <strong>{relResult.relationship}</strong>: {relResult.exists ? 'true' : 'false'}
              </div>
            )}
          </div>
        ) : null}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        onNodeClick={handleNodeClick}
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

export default function FamilyTree() {
  const personId = new URLSearchParams(window.location.search).get('personId') || 1;
  return <Flow personId={parseInt(personId, 10)} />;
}