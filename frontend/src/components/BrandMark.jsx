import { CryptoAuditMark } from './brand/CryptoAuditLogo';

/** The CryptoAudit symbol, sized for the app's sidebar and top bar. */
function BrandMark({ size = 24 }) {
  return <CryptoAuditMark size={size} className="brand-mark" />;
}

export default BrandMark;
