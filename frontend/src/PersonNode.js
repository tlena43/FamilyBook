import React from 'react';
import { Handle, Position } from '@xyflow/react';

/*
A node to display people on the family tree
*/


const hiddenHandle = {
  opacity: 0,
};

const spouseHandle = {
  opacity: 0,
  top: '50%',
  transform: 'translateY(-50%)',
};

export default function PersonNode({ data }) {
  return (
    <div
      style={{
        textAlign: 'center',
        width: 120,
      }}
    >
      <Handle type="target" position={Position.Top} id="top" style={hiddenHandle} />
      <Handle type="source" position={Position.Bottom} id="bottom" style={hiddenHandle} />

      <Handle type="target" position={Position.Left} id="left" style={hiddenHandle} />
      <Handle type="source" position={Position.Right} id="right" style={hiddenHandle} />

      <Handle type="target" position={Position.Left} id="spouse-left" style={spouseHandle} />
      <Handle type="source" position={Position.Right} id="spouse-right" style={spouseHandle} />

      <div style={{ fontWeight: 'bold' }}>{data.label}</div>
      <div style={{ fontSize: '12px' }}>
        {data.years}
      </div>
    </div>
  );
}