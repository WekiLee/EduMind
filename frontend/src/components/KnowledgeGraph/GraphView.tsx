import { useMemo, useRef, useState } from 'react';

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

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
}

interface EdgeVisual {
  stroke: string;
  strokeWidth: number;
  label: string;
  strokeDasharray?: string;
}

interface Viewport {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface PanStart {
  clientX: number;
  clientY: number;
  viewport: Viewport;
}

const VIEWBOX_WIDTH = 960;
const VIEWBOX_HEIGHT = 640;
const CENTER_X = VIEWBOX_WIDTH / 2;
const CENTER_Y = VIEWBOX_HEIGHT / 2;
const RING_RADIUS = 235;
const NODE_RADIUS = 28;
const DEFAULT_VIEWPORT = { x: 0, y: 0, width: VIEWBOX_WIDTH, height: VIEWBOX_HEIGHT };
const MIN_VIEWBOX_WIDTH = 420;
const MAX_VIEWBOX_WIDTH = 1500;

const statusColor = (status?: string, mastery?: number): string => {
  if (status === 'completed' && (mastery ?? 0) >= 0.8) return '#22c55e';   // 绿色
  if (status === 'completed') return '#86efac';                              // 浅绿
  if (status === 'learning') return '#f59e0b';                              // 橙色
  if (mastery && mastery > 0) return '#facc15';                              // 黄色
  return '#d1d5db';                                                           // 灰色
};

const edgeStyle = (type: string): EdgeVisual => {
  switch (type) {
    case 'PREREQUISITE': return { stroke: '#6366f1', strokeWidth: 2, label: '前置依赖' };
    case 'RELATED':      return { stroke: '#94a3b8', strokeWidth: 1.5, strokeDasharray: '6 6', label: '关联' };
    case 'EXTENDS':      return { stroke: '#22c55e', strokeWidth: 1.5, strokeDasharray: '5 5', label: '延伸' };
    default:             return { stroke: '#94a3b8', strokeWidth: 1, label: type || '关系' };
  }
};

const truncateTitle = (title: string): string => (
  title.length > 12 ? `${title.substring(0, 12)}...` : title
);

const buildLayout = (nodes: GraphNode[], currentNodeId?: string): PositionedNode[] => {
  if (nodes.length === 0) return [];
  if (nodes.length === 1) return [{ ...nodes[0], x: CENTER_X, y: CENTER_Y }];

  const current = currentNodeId ? nodes.find((node) => node.id === currentNodeId) : undefined;
  const ringNodes = current ? nodes.filter((node) => node.id !== current.id) : nodes;
  const positionedRing = ringNodes.map((node, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / ringNodes.length;
    return {
      ...node,
      x: CENTER_X + Math.cos(angle) * RING_RADIUS,
      y: CENTER_Y + Math.sin(angle) * RING_RADIUS,
    };
  });

  if (!current) return positionedRing;
  return [{ ...current, x: CENTER_X, y: CENTER_Y }, ...positionedRing];
};

export default function GraphView({ nodes, edges, currentNodeId, onNodeClick, width = '100%', height = '100%' }: GraphViewProps) {
  const [viewport, setViewport] = useState<Viewport>(DEFAULT_VIEWPORT);
  const panStartRef = useRef<PanStart | null>(null);
  const positionedNodes = useMemo(() => buildLayout(nodes, currentNodeId), [nodes, currentNodeId]);
  const nodeById = useMemo(
    () => new Map(positionedNodes.map((node) => [node.id, node])),
    [positionedNodes]
  );

  if (nodes.length === 0) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-gray-400" style={{ width, height }}>
        暂无知识图谱数据
      </div>
    );
  }

  const handleWheel = (event: React.WheelEvent<SVGSVGElement>) => {
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    const pointerXRatio = (event.clientX - rect.left) / rect.width;
    const pointerYRatio = (event.clientY - rect.top) / rect.height;
    const scale = event.deltaY > 0 ? 1.12 : 0.88;
    const nextWidth = Math.min(MAX_VIEWBOX_WIDTH, Math.max(MIN_VIEWBOX_WIDTH, viewport.width * scale));
    const nextHeight = nextWidth * (VIEWBOX_HEIGHT / VIEWBOX_WIDTH);
    const svgX = viewport.x + pointerXRatio * viewport.width;
    const svgY = viewport.y + pointerYRatio * viewport.height;

    setViewport({
      x: svgX - pointerXRatio * nextWidth,
      y: svgY - pointerYRatio * nextHeight,
      width: nextWidth,
      height: nextHeight,
    });
  };

  const handlePointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    const target = event.target as Element;
    if ((event.pointerType === 'mouse' && event.button !== 0) || target.closest('[data-node-id]')) return;
    panStartRef.current = {
      clientX: event.clientX,
      clientY: event.clientY,
      viewport,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!panStartRef.current) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const dx = ((event.clientX - panStartRef.current.clientX) / rect.width) * panStartRef.current.viewport.width;
    const dy = ((event.clientY - panStartRef.current.clientY) / rect.height) * panStartRef.current.viewport.height;
    setViewport({
      ...panStartRef.current.viewport,
      x: panStartRef.current.viewport.x - dx,
      y: panStartRef.current.viewport.y - dy,
    });
  };

  const handlePointerEnd = (event: React.PointerEvent<SVGSVGElement>) => {
    panStartRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  return (
    <div className="h-full min-h-[360px]" style={{ width, height }}>
      <svg
        viewBox={`${viewport.x} ${viewport.y} ${viewport.width} ${viewport.height}`}
        className="h-full w-full cursor-grab active:cursor-grabbing"
        role="img"
        aria-label="知识图谱"
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerEnd}
        onPointerCancel={handlePointerEnd}
        onDoubleClick={() => setViewport(DEFAULT_VIEWPORT)}
      >
        {edges.map((edge, index) => {
          const source = nodeById.get(edge.source);
          const target = nodeById.get(edge.target);
          if (!source || !target) return null;

          const visual = edgeStyle(edge.type);
          return (
            <line
              key={`${edge.source}-${edge.target}-${index}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={visual.stroke}
              strokeWidth={visual.strokeWidth}
              strokeDasharray={visual.strokeDasharray}
              strokeLinecap="round"
              opacity={0.72}
            >
              <title>{visual.label}</title>
            </line>
          );
        })}

        {positionedNodes.map((node) => {
          const isCurrent = node.id === currentNodeId;
          return (
            <g
              key={node.id}
              role="button"
              tabIndex={0}
              data-node-id={node.id}
              className="cursor-pointer outline-none"
              onClick={() => onNodeClick(node.id)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  onNodeClick(node.id);
                }
              }}
            >
              <circle
                cx={node.x}
                cy={node.y}
                r={isCurrent ? NODE_RADIUS + 5 : NODE_RADIUS}
                fill={statusColor(node.status, node.mastery)}
                stroke={isCurrent ? '#6366f1' : '#94a3b8'}
                strokeWidth={isCurrent ? 4 : 2}
              />
              <text
                x={node.x}
                y={node.y + NODE_RADIUS + 18}
                textAnchor="middle"
                className="select-none fill-gray-700 text-[13px]"
              >
                {truncateTitle(node.title || node.id)}
              </text>
              <title>{`${node.title}\n掌握度: ${((node.mastery ?? 0) * 100).toFixed(0)}%\n状态: ${node.status || '未开始'}`}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
