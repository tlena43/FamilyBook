// useState -> store data (nodes, edges, loading, error)
// useEffect -> run code when the component loads or updates
// ReactFlow -> main graph renderer
// Background / Controls / MiniMap -> UI helpers
import { useState, useEffect } from 'react';
import { ReactFlow, Background, Controls, MiniMap } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Test Data:
// id -> unique ID for each node
// data.label -> info displayed in each node
// position -> where node appears
// handles -> custom info for connection points
const testNodes = [
  {
    id: "1",
    data: { label: "Grandpa", handles: [false, true] },
    position: { x: 200, y: 0 },
  },
  {
    id: "2",
    data: { label: "Grandma", handles: [false, true] },
    position: { x: 400, y: 0 },
  },
  {
    id: "3",
    data: { label: "Dad", handles: [true, true] },
    position: { x: 300, y: 150 },
  },
  {
    id: "4",
    data: { label: "Mom", handles: [false, true] },
    position: { x: 500, y: 150 },
  },
  {
    id: "5",
    data: { label: "Me", handles: [true, false] },
    position: { x: 400, y: 300 },
  },
];

// Edge format: source (parent) -> target (child).
const testEdges = [
  { id: "e1-3", source: "1", target: "3" },
  { id: "e2-3", source: "2", target: "3" },
  { id: "e3-5", source: "3", target: "5" },
  { id: "e4-5", source: "4", target: "5" },
];

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

  // Fetching data... (this runs whenever personId changes or whenever the component mounts)
  useEffect(() => {
    const fetchFamilyTree = async () => {
      try {
        // Make the API call for the person in question (send auth token too):
        const authKey = localStorage.getItem('key');
        const response = await fetch(`http://127.0.0.1:5000/tree/${personId}`, {
          headers: {
            'X-api-key': authKey,
          }
        });
        
        if (!response.ok) throw new Error('Failed to fetch tree.');

        // Stores response as a JSON (backend tree gets plugged into React Flow here):
        const data = await response.json();
        setNodes(data.nodes);
        setEdges(data.edges);
        // Error handling...
      } catch (err) {
        setError(err.message);
        // Always stop loading...
      } finally {
        setLoading(false);
      }
    };

    // Guard: only fetch if the person ID exists.
    if (personId) fetchFamilyTree();
  }, [personId]);

  // Conditional rendering of loading / error states.
  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{ color: 'red' }}>Error: {error}</div>
 
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ReactFlow nodes={nodes} edges={edges} fitView> 
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