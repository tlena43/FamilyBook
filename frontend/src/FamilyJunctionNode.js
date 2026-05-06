import React from 'react';
import { Handle, Position } from '@xyflow/react';

/*
An invisible node designed to connect children to parents
*/

export default function FamilyJunctionNode({ data }) {
    const lineColor = data?.lineColor || 'rgba(0,0,0,0)';
    const jointHandle = {
        width: 3,
        height: 3,
        border: 'none',
        borderRadius: 8,
        background: lineColor,
        opacity: 1,
    };

    return (
        <div
            style={{
                width: 1,
                height: 1,

            }}
        >
            <Handle type="target" position={Position.Top} id="top" style={jointHandle} />
            <Handle type="source" position={Position.Bottom} id="bottom" style={jointHandle} />
        </div>
    );
}