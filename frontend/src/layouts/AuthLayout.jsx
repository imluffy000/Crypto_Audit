/** Signed-out page shell: one screen, with the brand palette (see brand.css and auth.css). */
function AuthLayout({ children }) {
  return (
    <div className="brand-page auth-page">
      <main className="auth-main page-anim">{children}</main>
    </div>
  );
}

export default AuthLayout;
