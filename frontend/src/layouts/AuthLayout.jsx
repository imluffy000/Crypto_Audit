/** Signed-out page shell: one screen, with its own scoped palette (see auth.css). */
function AuthLayout({ children }) {
  return (
    <div className="auth-page">
      <main className="auth-main">{children}</main>
    </div>
  );
}

export default AuthLayout;
