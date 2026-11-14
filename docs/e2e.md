# End-to-End Testing

Playwright exercises the React application through Chromium. The suite intercepts the `/api/v1/` calls with session and empty-family responses, so it never seeds, creates, updates, or removes financial data.

## Commands

From `frontend/`:

```sh
npm run e2e
npm run e2e:screenshots
```

Run these commands only when the Chromium revision required by the installed Playwright package is available. If it is not, a developer may install it explicitly with `npx playwright install chromium`; the test scripts never download a browser themselves.

`npm run e2e` starts the existing `npm run dev` Vite server on `127.0.0.1:5173` unless one is already running. Vite retains its normal `/api` proxy to the Django development server on `127.0.0.1:8000`; the foundational suite intercepts its requests before they reach that proxy.

To run against an already running frontend, set `E2E_BASE_URL`; Playwright will not start another Vite process:

```sh
E2E_BASE_URL=http://127.0.0.1:5173 npm run e2e
```

## Coverage

- Unauthenticated visitors see only the login screen and trigger no family-data request.
- Login succeeds through the existing CSRF/session API shape and reaches the administrator's empty initial-configuration state.
- An authorized non-administrator with an empty family sees the privacy boundary and no financial summary/export content.

## Screenshots

`npm run e2e:screenshots` captures the login, empty administrator dashboard, and privacy-safe empty member dashboard. Files are attached to the Playwright result for each test under `frontend/test-results/`; they are intentionally ignored because they may contain local UI state.

Playwright also captures a full-page screenshot automatically when an E2E test fails.
