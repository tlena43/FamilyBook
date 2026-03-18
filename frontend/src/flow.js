import { useState, useCallback } from 'react';
import { ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

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

const testEdges = [
  { id: "e1-3", source: "1", target: "3" },
  { id: "e2-3", source: "2", target: "3" },
  { id: "e3-5", source: "3", target: "5" },
  { id: "e4-5", source: "4", target: "5" },
];

function Flow() {
  const [nodes, setNodes] = useState(testNodes);
  const [edges, setEdges] = useState(testEdges);

 
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
      />
    </div>
  );
}

export default function FamilyTree(){
     return (
    <div id="family-tree-container">
      <Flow/>
    </div>
  ) 
}