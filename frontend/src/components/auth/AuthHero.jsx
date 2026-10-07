/** Left column of the sign-in page: a short title and the GitHub sign-in card. */
function AuthHero({ titleId, children }) {
  return (
    <section className="auth-hero" aria-labelledby={titleId}>
      <div className="auth-card">
        <div className="auth-card-head">
          <h1 id={titleId} className="auth-card-title">
            Sign in
          </h1>
          <p className="auth-card-lead">Continue with GitHub to start scanning.</p>
        </div>
        {children}
      </div>
    </section>
  );
}

export default AuthHero;
