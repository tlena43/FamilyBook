import React from 'react';
import { Handle, Position } from '@xyflow/react';

export default function FamilyJunctionNode() {
  return (
    <div
      style={{
        width: 1,
        height:1,
       
      }}
    >
      <Handle type="target" position={Position.Top} id="top"  />
      <Handle type="source" position={Position.Bottom} id="bottom"  style={{opacity:0}}/>
    </div>
  );
}