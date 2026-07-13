# Frontend — React 18 + Tailwind

## Structure

```
src/api/client.js        axios instance; JWT attached from localStorage; 401 -> logout
src/context/AuthContext  token / clientId / role state
src/components/          Navbar, ProtectedRoute, Loader
src/pages/               Home, Login (client+admin), Register (admin-only),
                         Dashboard, GenerateCertificate, GenerateId, TemplateDesigner
```

## Scripts

```bash
npm install
npm start        # dev server on :3000 (expects API on :5000)
npm run build    # production build
```

Set `REACT_APP_API_URL` to point at a non-default backend.

## Pages

- **Login** — client or admin mode; stores the JWT and role.
- **Register** — admin-only; creates client accounts.
- **Dashboard** — action cards + recent-certificates gallery.
- **AI Template Designer** — plain-English prompt -> agent-designed template,
  live preview via /renderPreview, one-click save.
