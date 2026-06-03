import { useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

interface GraphNode {
  id: string;
  title: string;
  difficulty: string;
  mastery?: number;
  status?: string;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

interface GraphViewProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  currentNodeId?: string;
  onNodeClick: (nodeId: string) => void;
  width?: string;
  height?: string;
}

const statusColor = (status?: string, mastery?: number): string => {
  if (status === 'completed' && (mastery ?? 0) >= 0.8) return '#22c55e';   // 绿色
  if (status === 'completed') return '#86efac';                              // 浅绿
  if (status === 'learning') return '#f59e0b';                              // 橙色
  if (mastery && mastery > 0) return '#facc15';                              // 黄色
  return '#d1d5db';                                                           // 灰色
};

const edgeStyle = (type: string): object => {
  switch (type) {
    case 'PREREQUISITE': return { color: '#6366f1', dashes: false, width: 2 };
    case 'RELATED':      return { color: '#94a3b8', dashes: true,  width: 1 };
    case 'EXTENDS':      return { color: '#22c55e', dashes: true,  width: 1.5 };
    default:             return { color: '#94a3b8', dashes: false, width: 1 };
  }
};

export default function GraphView({ nodes, edges, currentNodeId, onNodeClick, width = '100%', height = '100%' }: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;

    const visNodes = new DataSet(nodes.map((n) => ({
      id: n.id,
      label: n.title.length > 12 ? n.title.substring(0, 12) + '...' : n.title,
      color: {
        background: statusColor(n.status, n.mastery),
        border: n.id === currentNodeId ? '#6366f1' : '#94a3b8',
      },
      borderWidth: n.id === currentNodeId ? 3 : 1,
      size: n.id === currentNodeId ? 28 : 22,
      font: { size: 11, color: '#374151' },
      title: `${n.title}\n掌握度: ${((n.mastery ?? 0) * 100).toFixed(0)}%\n状态: ${n.status || '未开始'}`,
    }) as any));

    const visEdges = new DataSet(edges.map((e) => ({
      from: e.source,
      to: e.target,
      ...edgeStyle(e.type),
      title: e.type === 'PREREQUISITE' ? '前置依赖' : e.type === 'RELATED' ? '关联' : '延伸',
    }) as any));

    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        stabilization: { iterations: 100 },
      },
      interaction: {
        hover: true,
        zoomView: true,
        dragView: true,
      },
      edges: {
        smooth: { enabled: true, type: 'curvedCW', roundness: 0.1 },
      },
    };

    networkRef.current = new Network(containerRef.current, { nodes: visNodes, edges: visEdges }, options);

    networkRef.current.on('click', (params) => {
      if (params.nodes.length > 0) {
        onNodeClick(params.nodes[0]);
      }
    });

    return () => {
      networkRef.current?.destroy();
      networkRef.current = null;
    };
  }, [nodes, edges, currentNodeId]);

  return <div ref={containerRef} style={{ width, height }} />;
}
