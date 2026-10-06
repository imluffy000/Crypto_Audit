import DashboardLayout from '../layouts/DashboardLayout';

function ComingSoon({ title = 'Coming Soon', subtitle = 'This area will be implemented in the next product phase.' }) {
  return (
    <DashboardLayout>
      <div className="card-panel empty-state large">
        <div className="empty-icon">✦</div>
        <h3>{title}</h3>
        <p>{subtitle}</p>
      </div>
    </DashboardLayout>
  );
}

export default ComingSoon;
