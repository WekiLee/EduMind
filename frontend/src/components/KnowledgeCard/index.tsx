/** 知识卡片组件 — 按 domain_id 选择模板渲染 */

interface KnowledgeNode {
  id: string;
  title: string;
  summary: string;
  content: string;
  difficulty: string;
  domain_id: string;
  node_type: string;
  examples?: string[];
  code_snippets?: string[];
  prerequisites?: { id: string; title: string }[];
  related_nodes?: { id: string; title: string }[];
}

interface KnowledgeCardProps {
  node: KnowledgeNode;
}

/** 渲染内容：代码块用深色背景，普通文本正常显示 */
function renderContent(text: string) {
  if (!text) return null;
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    const codeMatch = part.match(/^```(\w*)\n?([\s\S]*?)```$/);
    if (codeMatch) {
      return (
        <pre key={i} className="bg-gray-900 text-green-400 p-3 rounded-lg overflow-x-auto my-2 text-xs leading-relaxed">
          <code>{codeMatch[2]}</code>
        </pre>
      );
    }
    return (
      <div key={i} className="whitespace-pre-wrap text-sm leading-relaxed mb-2">{part}</div>
    );
  });
}

/** 通用卡片 */
function DefaultCard({ node }: KnowledgeCardProps) {
  return <div>{renderContent(node.content)}</div>;
}

/** 数学卡片（含公式提示） */
function MathCard({ node }: KnowledgeCardProps) {
  return (
    <div>
      {node.content.includes('$$') && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-2 mb-3 text-xs text-yellow-700">
          ⚡ 数学公式使用 $$...$$ 包裹显示
        </div>
      )}
      {renderContent(node.content)}
    </div>
  );
}

/** 编程卡片（代码块自动高亮） */
function ProgrammingCard({ node }: KnowledgeCardProps) {
  return <div>{renderContent(node.content)}</div>;
}

/** 语言卡片 */
function LanguageCard({ node }: KnowledgeCardProps) {
  return <div>{renderContent(node.content)}</div>;
}

/** 历史卡片 */
function HistoryCard({ node }: KnowledgeCardProps) {
  return <div>{renderContent(node.content)}</div>;
}

/** 物理卡片 */
function PhysicsCard({ node }: KnowledgeCardProps) {
  return (
    <div>
      {node.content.includes('$$') && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-2 mb-3 text-xs text-yellow-700">
          ⚡ 物理公式使用 $$...$$ 包裹显示
        </div>
      )}
      {renderContent(node.content)}
    </div>
  );
}

const TEMPLATES: Record<string, React.FC<KnowledgeCardProps>> = {
  general: DefaultCard,
  math: MathCard,
  programming: ProgrammingCard,
  language: LanguageCard,
  history: HistoryCard,
  physics: PhysicsCard,
};

export default function KnowledgeCard({ node }: KnowledgeCardProps) {
  const CardTemplate = TEMPLATES[node.domain_id] || DefaultCard;
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full">{node.difficulty}</span>
        <span className="text-xs bg-gray-50 text-gray-500 px-2 py-0.5 rounded-full">{node.node_type}</span>
        <span className="text-xs bg-gray-50 text-gray-400 px-2 py-0.5 rounded-full">{node.domain_id}</span>
      </div>
      <h2 className="text-lg font-bold mb-1">{node.title}</h2>
      <p className="text-gray-500 text-sm mb-2">{node.summary}</p>
      <CardTemplate node={node} />
      {node.examples && node.examples.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-500 mb-2">📎 示例</p>
          {node.examples.map((ex: string, i: number) => (
            <pre key={i} className="bg-gray-900 text-green-400 p-3 rounded-lg overflow-x-auto my-1 text-xs leading-relaxed">{ex}</pre>
          ))}
        </div>
      )}
      {node.code_snippets && node.code_snippets.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-500 mb-2">💻 代码</p>
          {node.code_snippets.map((code: string, i: number) => (
            <pre key={i} className="bg-gray-900 text-green-400 p-3 rounded-lg overflow-x-auto my-1 text-xs leading-relaxed">{code}</pre>
          ))}
        </div>
      )}
    </div>
  );
}
