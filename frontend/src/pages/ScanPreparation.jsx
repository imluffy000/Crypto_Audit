import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, Clock3, Database, ShieldAlert, Sparkles } from 'lucide-react';
import DashboardLayout from '../layouts/DashboardLayout';

const steps = [
  'Repository uploaded',
  'Repository structure analyzed',
  'Files validated',
  'Security scan',
  'Cryptographic analysis',
  'AI analysis',
  'Repair validation',
  'Risk scoring',
  'Report generation',
];

function ScanPreparation() {
  const navigate = useNavigate();

  return (
    <DashboardLayout>
      <div className="page-header">
        <div>
          <p className="eyebrow">Audit workflow</p>
          <h1>Preparing your security audit</h1>
        </div>
      </div>

      <div className="card-panel stage-panel">
        <div className="stage-header">
          <Sparkles size={16} />
          <span>Backend integration required</span>
        </div>

        <ul className="step-list">
          {steps.map((step, index) => {
            const complete = index < 3;
            return (
              <li key={step} className={complete ? 'complete' : 'pending'}>
                <span className="step-marker">{complete ? <Check size={12} /> : <Clock3 size={12} />}</span>
                <span>{step}</span>
              </li>
            );
          })}
        </ul>

        <div className="alert-box warning">
          <ShieldAlert size={15} />
          <div>
            <strong>Future backend modules are not yet connected.</strong>
            <p>This frontend demonstrates the workflow only. The actual scan engine and analysis pipeline will be added in the next phase.</p>
          </div>
        </div>

        <div className="footer-actions">
          <button type="button" className="secondary-button" onClick={() => navigate('/repositories/review')}>
            <ArrowLeft size={14} /> Return to Repository
          </button>
        </div>
      </div>
    </DashboardLayout>
  );
}

export default ScanPreparation;
