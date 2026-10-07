# CryptoAudit logo

The symbol is a geometric shield whose counter is an open **C**, for CryptoAudit and for code, with a
single lime point at its centre: the bit that was audited. It has three shapes only, so it stays
recognisable at 16 px.

| File | Use |
|---|---|
| `cryptoaudit-logo.svg` | Symbol + wordmark, full colour: website, docs, README |
| `cryptoaudit-logo-dark.svg` | Single near-black colour, for light backgrounds and print |
| `cryptoaudit-logo-white.svg` | Single white colour, for dark backgrounds |
| `cryptoaudit-symbol.svg` | Symbol only, full colour: navbar, dashboard, favicon |
| `cryptoaudit-symbol-dark.svg`, `cryptoaudit-symbol-white.svg` | Symbol only, single colour |
| `cryptoaudit-app-icon.svg` | Rounded teal tile for app icons and the GitHub repository avatar |

In the website the same geometry lives in `frontend/src/components/brand/CryptoAuditLogo.jsx`
(`<CryptoAuditLogo variant="color | dark | white" />`, or `<CryptoAuditMark />` for the symbol only), and
`frontend/public/favicon.svg` is the full-colour symbol.

## Colour

| Role | Colour |
|---|---|
| Symbol | `#0F766E` |
| "C" | `#FFFFFF` |
| Point | `#D9F99D` |
| Wordmark | `#17201D` (white on dark backgrounds) |

The single-colour versions cut the "C" and the point out of the shield, so they work on any
background. No gradients, shadows or outlines.

## Wordmark

"CryptoAudit" as one word, semibold (600), letter-spacing −0.02em, in Inter (falling back to the
system sans-serif). The symbol is 1.8× the wordmark's cap height and sits 10 px from it at a 22 px
wordmark.

## Spacing and size

- Keep clear space around the logo equal to the width of the "C" stroke times four (about a quarter
  of the symbol's width).
- Smallest sizes: symbol 16 px; symbol + wordmark 96 px wide.
- Don't recolour the point, rotate or outline the symbol, or put the full-colour symbol on teal.
