import { useMemo, useState, useEffect } from 'react';
import { ReactFlow, Background, Controls, MiniMap } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import PersonNode from './PersonNode.js';
import FamilyJunctionNode from './FamilyJunctionNode.js';


// This function fetches tree data, stores it, and passes it to React Flow.
function Flow({ personId }) {
  // Nodes -> people
  const [nodes, setNodes] = useState([]);
  // Edges -> relationships
  const [edges, setEdges] = useState([]);
  // Loading -> whether or not fetch is in progress
  const [loading, setLoading] = useState(true);
  // Error -> for failures
  const [error, setError] = useState(null);

  // Relationship query UI state
  const [relPerson1, setRelPerson1] = useState('');
  const [relPerson2, setRelPerson2] = useState('');
  const [relationship, setRelationship] = useState('sibling');
  const [relResult, setRelResult] = useState(null);
  const [relLoading, setRelLoading] = useState(false);
  const [relError, setRelError] = useState(null);

  // Node-click selection (more intuitive than typing IDs)
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

  // Custom node renderers (restores proper handles/branch junction rendering)
  const nodeTypes = useMemo(
    () => ({
      person: PersonNode,
      familyJunction: FamilyJunctionNode,
    }),
    []
  );

  // keep the text inputs in sync with node picks
  useEffect(() => {
    setRelPerson1(selected1 != null ? String(selected1) : '');
  }, [selected1]);

  useEffect(() => {
    setRelPerson2(selected2 != null ? String(selected2) : '');
  }, [selected2]);

  // Apply a visual highlight to selected nodes
  useEffect(() => {
    const baseStyle = {
      borderRadius: 8,
      border: '2px solid #333',
      padding: '10px',
    };

    setNodes((prev) =>
      (prev ?? []).map((n) => {
        const idNum = parseInt(n.id, 10);
        const isSelected1 = Number.isInteger(idNum) && idNum === selected1;
        const isSelected2 = Number.isInteger(idNum) && idNum === selected2;

        const outline = isSelected1
          ? { outline: '4px solid #2563eb', outlineOffset: 2 }
          : isSelected2
            ? { outline: '4px solid #16a34a', outlineOffset: 2 }
            : { outline: 'none' };

        return {
          ...n,
          style: {
            ...baseStyle,
            ...(n.style || {}),
            ...outline,
          },
        };
      })
    );
  }, [selected1, selected2]);

  function clearSelection() {
    setSelected1(null);
    setSelected2(null);
    setRelResult(null);
    setRelError(null);
  }

  function handleNodeClick(_evt, node) {
    const idNum = parseInt(node?.id, 10);
    if (!Number.isInteger(idNum)) return;

    // Click behavior:
    // - first click sets Person 1
    // - second click sets Person 2
    // - third click starts over with Person 1
    if (selected1 == null || (selected1 != null && selected2 != null)) {
      setSelected1(idNum);
      setSelected2(null);
      setRelResult(null);
      setRelError(null);
      return;
    }

    if (selected2 == null) {
      // allow clicking same node to deselect
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

  // Fetching data... (this runs whenever personId changes or whenever the component mounts)
  useEffect(() => {
    const fetchFamilyTree = async () => {
      try {
        const authKey = localStorage.getItem('key');
        const response = await fetch(`http://127.0.0.1:5000/tree/${personId}`, {
          headers: {
            'X-api-key': authKey,
          }
        });

        if (!response.ok) throw new Error('Failed to fetch tree.');

        const data = await response.json();

        // Ensure node styles keep a baseline shape (selection highlight is layered later)
        const baseStyle = {
          borderRadius: 8,
          border: '2px solid #333',
          padding: '10px',
        };

        setNodes((data.nodes ?? []).map((n) => ({
          ...n,
          style: {
            ...baseStyle,
            ...(n.style || {}),
          },
        })));
        setEdges(data.edges ?? []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (personId) fetchFamilyTree();
  }, [personId]);

  // Conditional rendering of loading / error states.
  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{ color: 'red' }}>Error: {error}</div>

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {/* Relationship Query Panel */}
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

// Renders tree for person with ID from URL params or context.
export default function FamilyTree(){
  // Get personId from URL params, props, or context.
  // For now, you can pass it as a prop or get it from useParams()
  // Example: const { personId } = useParams(); if using React Router
  const personId = new URLSearchParams(window.location.search).get('personId') || 1;
  return <Flow personId={parseInt(personId)} />;
}