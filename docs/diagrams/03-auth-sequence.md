# Sign-in, switching accounts and signing out

CryptoAudit uses a **GitHub OAuth App** (web flow). The backend handles the whole exchange; the
browser only ever holds an HttpOnly session cookie, never the GitHub token.

## Sign in

1. `GET /api/auth/github/login` creates a single-use `state`, stores it server-side **and** sets it
   in an HttpOnly cookie scoped to `/api/auth`, then redirects to GitHub's consent page.
2. GitHub redirects back to `/api/auth/github/callback?code&state`.
3. The callback consumes the server-side state first (so it can never be replayed) and requires the
   cookie copy to match. Otherwise it redirects to `/#/login?error=invalid_state`.
4. The code is exchanged for an access token, the GitHub profile is read, any session still open in
   this browser is ended (and its token revoked), and a new session is created.
5. The browser receives a session cookie (`HttpOnly`, `SameSite=Lax`, `Secure` behind HTTPS) and
   lands on the dashboard.

Any unexpected error in the callback redirects to `/#/login?error=server_error` instead of showing
a bare error page; details go to the server log.

## Switch account

The account menu's **Switch account** (or **Use a different GitHub account** on the sign-in page)
signs out, then starts sign-in with `prompt=select_account`, so GitHub shows its account picker
instead of silently reusing the account you are signed in to on github.com.

## Sign out

`POST /api/auth/logout` deletes the session and revokes the token at GitHub (OAuth App tokens never
expire on their own). Revocation is best effort; you can also revoke access in GitHub settings.

## Storage and scopes

| Item | Stored as |
|---|---|
| Session id (cookie) | hashed in the web store |
| GitHub access token | encrypted at rest (Fernet), server only |
| OAuth state | single use, short-lived |

Scopes: `read:user repo` when `CRYPTOAUDIT_GITHUB_REPO_ACCESS=private` (the default; needed for
private repositories) or `read:user` when `public`. CryptoAudit only ever sends read requests.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    actor U as Developer
    participant FE as Frontend
    participant API as /api/auth
    participant ST as Web store
    participant GH as GitHub

    rect rgb(240, 245, 252)
    Note over U,GH: Sign in
    U->>FE: Continue with GitHub
    FE->>API: GET /github/login [?select_account=true]
    API->>ST: create_oauth_state()
    API-->>U: 302 to github.com/login/oauth/authorize<br/>(client_id, scope, state, prompt?) + state cookie
    U->>GH: consent (or pick account)
    GH-->>U: 302 /api/auth/github/callback?code&state
    U->>API: GET /github/callback
    API->>ST: consume_oauth_state(state)
    alt state missing, reused or cookie mismatch
        API-->>U: 302 /#/login?error=invalid_state
    else valid
        API->>GH: POST /login/oauth/access_token (code)
        GH-->>API: access token
        API->>GH: GET /user
        GH-->>API: profile
        API->>ST: end previous session in this browser (revoke its token)
        API->>ST: create_session(user, encrypted token)
        API-->>U: 302 /#/dashboard + HttpOnly SameSite=Lax session cookie
    end
    end

    rect rgb(245, 250, 242)
    Note over U,GH: Every API call
    FE->>API: GET /api/auth/me (cookie)
    API->>ST: get_session(hash(cookie))
    API-->>FE: {id, login, name, avatar} or 401
    end

    rect rgb(252, 246, 238)
    Note over U,GH: Switch account
    U->>FE: Account menu → Switch account
    FE->>API: POST /logout
    API->>ST: delete session
    API->>GH: DELETE /applications/{client_id}/token
    FE->>API: GET /github/login?select_account=true
    Note over U,GH: continues as Sign in, GitHub shows its account picker
    end

    rect rgb(252, 240, 240)
    Note over U,GH: Sign out
    U->>FE: Sign out
    FE->>API: POST /logout
    API->>ST: delete session
    API->>GH: revoke token (best effort, OAuth tokens never expire)
    API-->>FE: 204 + cookie cleared
    end
```
