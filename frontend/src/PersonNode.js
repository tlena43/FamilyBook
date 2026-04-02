import React from 'react';
import { Handle, Position } from '@xyflow/react';

export default function PersonNode({ data }) {
  return (
    <div
      style={{
        textAlign: 'center',
        width: 120,
      }}
    >
      <Handle type="target" position={Position.Top} id="top" style={{opacity: 0}} />
      <Handle type="target" position={Position.Left} id="left"  style={{opacity: 0}}/>
      <Handle type="source" position={Position.Right} id="right" style={{opacity: 0}}/>
      <Handle type="source" position={Position.Bottom} id="bottom" style={{opacity: 0}}/>

      <div style={{ fontWeight: 'bold' }}>{data.label}</div>
      <div style={{ fontSize: '12px' }}>
        {data.years}
      </div>
    </div>
  );
}