import { CheckCircle2, TriangleAlert } from 'lucide-react';

/** A pill naming an algorithm or API with a verdict icon: `tone` is 'success' or 'warning'. */
function AlgorithmBadge({ name, tone = 'success', className = '', style }) {
  const Icon = tone === 'warning' ? TriangleAlert : CheckCircle2;
  return (
    <span className={`algo-badge tone-${tone} ${className}`.trim()} style={style}>
      {name}
      <Icon size={16} aria-hidden="true" />
    </span>
  );
}

export default AlgorithmBadge;
