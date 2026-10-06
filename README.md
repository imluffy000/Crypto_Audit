# CryptoAudit

CryptoAudit is a frontend prototype for reviewing repositories for cryptographic security issues.

## Preview

Open the [CryptoAudit preview](https://imluffy000.github.io/Crypto_Audit/). GitHub Actions publishes the preview whenever changes are pushed to `main`.

The current preview uses mock sign-in and repository data. GitHub and Google OAuth, private repository access, and the audit backend are not connected yet.

## Run locally

```sh
npm install
npm run dev
```

Create a production build with `npm run build`.

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
