"use client";
import { useCallback, useMemo, useState, useRef } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  MarkerType,
  ReactFlowProvider,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";

const NODE_COLORS: Record<string, string> = {
  data: "#3b82f6",
  factor: "#8b5cf6",
  condition: "#f59e0b",
  signal: "#22c55e",
};

interface Props {
  config: any;
  onChange: (config: any) => void;
  onDropFactor?: (factor: { key: string; label: string }, position: { x: number; y: number }) => void;
}

export default function StrategyCanvas({ config, onChange, onDropFactor }: Props) {
  const conditions = config?.conditions?.children || [];
  const logic = config?.conditions?.logic || "AND";
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  const initialNodes: Node[] = useMemo(() => {
    const nodes: Node[] = [
      {
        id: "data-source",
        type: "default",
        position: { x: 50, y: 50 },
        data: { label: "数据源\n沪深300" },
        style: { background: "#eff6ff", border: "2px solid #3b82f6", borderRadius: 8, padding: 12, fontSize: 12, width: 100 },
      },
      {
        id: "signal-gen",
        type: "default",
        position: { x: 450, y: 50 },
        data: { label: "生成信号\n买入 0/1" },
        style: { background: "#f0fdf4", border: "2px solid #22c55e", borderRadius: 8, padding: 12, fontSize: 12, width: 100 },
      },
    ];

    const logicNode = {
      id: "logic",
      type: "default",
      position: { x: 250, y: 50 },
      data: { label: `条件组合\n${logic}` },
      style: { background: "#fffbeb", border: "2px solid #f59e0b", borderRadius: 8, padding: 12, fontSize: 12, width: 100 },
    };
    nodes.splice(1, 0, logicNode);

    conditions.forEach((c: any, i: number) => {
      nodes.push({
        id: `condition-${i}`,
        type: "default",
        position: { x: 250, y: 130 + i * 70 },
        data: { label: `条件 ${i + 1}\n${formatCondition(c)}` },
        style: { background: "#fff", border: "2px solid #e2e8f0", borderRadius: 8, padding: 12, fontSize: 11, width: 150 },
      });
    });

    return nodes;
  }, [config]);

  const initialEdges: Edge[] = useMemo(() => {
    const edges: Edge[] = [
      {
        id: "data-logic",
        source: "data-source",
        target: "logic",
        markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
        style: { stroke: "#94a3b8", strokeWidth: 2 },
      },
      {
        id: "logic-signal",
        source: "logic",
        target: "signal-gen",
        markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
        style: { stroke: "#94a3b8", strokeWidth: 2 },
      },
    ];

    conditions.forEach((_: any, i: number) => {
      edges.push({
        id: `logic-cond-${i}`,
        source: "logic",
        target: `condition-${i}`,
        style: { stroke: "#cbd5e1", strokeWidth: 1.5, strokeDasharray: "5 5" },
      });
    });

    return edges;
  }, [config]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (conn: Connection) => setEdges((eds) => addEdge(conn, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const raw = event.dataTransfer.getData("application/quantdesk-factor");
      if (!raw || !reactFlowInstance) return;
      const factor = JSON.parse(raw);
      const bounds = reactFlowWrapper.current?.getBoundingClientRect();
      if (!bounds) return;
      const position = reactFlowInstance.project({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });
      onDropFactor?.(factor, position);
    },
    [reactFlowInstance, onDropFactor]
  );

  return (
    <div ref={reactFlowWrapper} className="flex-1 h-full" onDragOver={onDragOver} onDrop={onDrop}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        fitView
        fitViewOptions={{ padding: 0.3 }}
      >
        <Background color="#e2e8f0" gap={20} />
        <Controls />
        <MiniMap
          nodeColor={(n) => {
            if (n.id === "data-source") return "#3b82f6";
            if (n.id === "signal-gen") return "#22c55e";
            if (n.id === "logic") return "#f59e0b";
            return "#94a3b8";
          }}
        />
      </ReactFlow>
    </div>
  );
}

function formatCondition(c: any): string {
  if (c.type === "compare") {
    const left = c.left?.factor || c.left?.label || "?";
    const right = c.right?.factor || c.right?.value || "?";
    let op = c.op;
    if (op === ">") op = "大于";
    if (op === "<") op = "小于";
    return `${left} ${op} ${right}`;
  }
  if (c.type === "cross") {
    return `${c.fast?.factor || "?"} ↔ ${c.slow?.factor || "?"}`;
  }
  return "条件";
}
