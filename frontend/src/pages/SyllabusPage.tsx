import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { ArrowLeft, GripVertical, Save } from 'lucide-react';
import { LoadingSpinner } from '../components/common';
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext, verticalListSortingStrategy, useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface SyllabusModule {
  module_name: string;
  order: number;
  node_ids: string[];
  nodes?: { id: string; title?: string; status: string; mastery: number }[];
}

function SortableItem({ id, children, disabled }: { id: string; children: React.ReactNode; disabled?: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id, disabled });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1 };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2 group cursor-grab active:cursor-grabbing">
      {children}
    </div>
  );
}

function ModuleSortableItem({ id, children }: { id: string; children: React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const style = { transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.5 : 1 };
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} className="bg-white rounded-xl border border-gray-100 p-4">
      {children}
    </div>
  );
}

export default function SyllabusPage() {
  const { pathId } = useParams();
  const navigate = useNavigate();
  const [path, setPath] = useState<any>(null);
  const [modules, setModules] = useState<SyllabusModule[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  useEffect(() => {
    if (!pathId) return;
    api.get(`/learning-paths/${pathId}`).then(({ data }) => {
      setPath(data.data);
      setModules(data.data.syllabus || []);
    });
  }, [pathId]);

  // 模块内节点拖拽结束
  const handleNodeDragEnd = (moduleIdx: number, event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const newModules = [...modules];
    const nodeIds = [...newModules[moduleIdx].node_ids];
    const oldIdx = nodeIds.indexOf(active.id as string);
    const newIdx = nodeIds.indexOf(over.id as string);
    if (oldIdx === -1 || newIdx === -1) return;
    nodeIds.splice(oldIdx, 1);
    nodeIds.splice(newIdx, 0, active.id as string);
    newModules[moduleIdx] = { ...newModules[moduleIdx], node_ids: nodeIds };
    setModules(newModules);
  };

  // 模块拖拽结束
  const handleModuleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIdx = modules.findIndex((m) => m.module_name === active.id);
    const newIdx = modules.findIndex((m) => m.module_name === over.id);
    if (oldIdx === -1 || newIdx === -1) return;
    const newModules = [...modules];
    const [moved] = newModules.splice(oldIdx, 1);
    newModules.splice(newIdx, 0, moved);
    setModules(newModules.map((m, i) => ({ ...m, order: i + 1 })));
  };

  const handleConfirm = async () => {
    setSaving(true);
    try {
      const syllabus = modules.map((m) => ({ module_name: m.module_name, order: m.order, node_ids: m.node_ids }));
      await api.patch(`/learning-paths/${pathId}`, syllabus);
      setSaved(true);
      setTimeout(() => navigate(`/learn/${pathId}`), 800);
    } catch (err) {
      console.error('保存失败', err);
    } finally {
      setSaving(false);
    }
  };

  if (!path) return <LoadingSpinner text="加载大纲..." />;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <button onClick={() => navigate(`/learn/${pathId}`)} className="flex items-center gap-1 text-gray-500 mb-4 hover:text-gray-700">
        <ArrowLeft size={16} /> 返回
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{path.topic}</h1>
          <p className="text-gray-400 text-sm mt-1">拖拽模块和知识点调整学习顺序</p>
        </div>
        <button onClick={handleConfirm} disabled={saving || saved}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm">
          <Save size={16} /> {saved ? '已保存 ✓' : saving ? '保存中...' : '确认并开始学习'}
        </button>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleModuleDragEnd}>
        <SortableContext items={modules.map((m) => m.module_name)} strategy={verticalListSortingStrategy}>
          <div className="space-y-4">
            {modules.map((module, mi) => (
              <ModuleSortableItem key={module.module_name} id={module.module_name}>
                {/* 模块头 */}
                <div className="flex items-center gap-2 mb-3">
                  <GripVertical size={16} className="text-gray-300 cursor-grab" />
                  <span className="bg-indigo-100 text-indigo-600 text-xs px-2 py-0.5 rounded-full">模块 {mi + 1}</span>
                  <input value={module.module_name}
                    onChange={(e) => {
                      const newModules = [...modules];
                      newModules[mi] = { ...newModules[mi], module_name: e.target.value };
                      setModules(newModules);
                    }}
                    className="font-medium bg-transparent border-b border-transparent hover:border-gray-300 focus:border-indigo-500 outline-none text-sm" />
                  <span className="text-xs text-gray-400 ml-auto">{module.node_ids.length} 个知识点</span>
                </div>

                {/* 节点列表（可拖拽排序） */}
                <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(e) => handleNodeDragEnd(mi, e)}>
                  <SortableContext items={module.node_ids} strategy={verticalListSortingStrategy}>
                    <div className="space-y-1 ml-6">
                      {module.node_ids.map((nid, ni) => {
                        const node = (module.nodes || []).find((n) => n.id === nid);
                        return (
                          <SortableItem key={nid} id={nid}>
                            <span className="text-gray-300 text-xs w-5">{ni + 1}.</span>
                            <span className="flex-1 truncate">{node?.title || nid.substring(0, 12)}</span>
                            {node?.status === 'completed' && <span className="text-green-500 text-xs">✅</span>}
                          </SortableItem>
                        );
                      })}
                    </div>
                  </SortableContext>
                </DndContext>
              </ModuleSortableItem>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {saved && (
        <div className="fixed bottom-6 right-6 bg-green-600 text-white px-6 py-3 rounded-xl shadow-lg text-sm">
          ✅ 大纲已保存，即将进入学习...
        </div>
      )}
    </div>
  );
}
