# SportHub

SportHub runs on React/TypeScript (Vite), Django REST Framework and its own PostgreSQL database. PHP, Apache and MySQL are no longer application dependencies.

## Local development

For the existing bundled Windows environment, run from this folder:

```powershell
.\scripts\start.ps1
```

Open **http://localhost:5173**. The frontend proxies `/api/` and `/media/` to Django on port 8000. PostgreSQL uses port 55432 and database `sporthub_next`.

To stop the local services:

```powershell
.\scripts\stop.ps1
```

For frontend setup and verification commands, see [frontend/README.md](frontend/README.md). Python dependencies are in `backend/requirements.txt`; backend settings use `backend/.env.example` and the private `backend/.env`. The frontend has its own optional `.env.example` for its API proxy. `project-support/deployment/.env.production.example` is the separate deployment template. Do not recreate the removed root legacy `.env`.

Create the first staff account from `backend`:

```powershell
..\.venv\Scripts\python.exe manage.py createsuperuser
```

No sample accounts, products or orders are inserted into the application database. Staff can create categories/products at `/admin/catalog`.

## Available features

- Registration, customer/staff login, profile/password updates and logout.
- Home, shop filters/search, categories, product details, About and Contact.
- Cart, wishlist, selected checkout with cash on delivery and order history.
- Khalti checkout, payment history, verified receipts, pending/failure recovery and login recovery on return (requires merchant configuration).
- Staff catalog, dashboard, order fulfillment, customer/staff accounts and messages.

Khalti application flows have automated contract coverage; an actual merchant sandbox transaction is still required. Outlet maps and production cutover checks remain pending. See [payment setup and verification](docs/PAYMENTS.md), [the migration checklist](docs/MIGRATION.md), [API contract](docs/API.md), and [architecture](docs/ARCHITECTURE.md).

## Folder layout

The main folders at root are `frontend/`, `backend/`, `docs/`, and `scripts/`. Older uploads, reference images, and deployment files are grouped under [project-support/](project-support/README.md). Hidden local runtime/tool folders remain at root to preserve installed paths. No files were deleted during this organization pass.

## Legacy cleanup

The PHP pages, legacy SQL dump, old CSS/JavaScript, duplicate static images and obsolete root environment files were removed in an earlier cleanup after a verified private backup. The current app's static images are in `frontend/public/images`. Unique original uploads are retained in `project-support/legacy-uploads/`, and the reference-image directory is retained as `project-support/reference-images/`; they are not imported into the database or served by the new app.

The private legacy archives are outside this repository at `C:\Users\ACER\sporthub-migration-backups`; they may contain sensitive configuration and must not be published. Historical PHP filenames in the audit documents refer to those archived sources. `.htaccess` remains to protect environment files/logs if this workspace is exposed by the local XAMPP installation; use port 5173 to run the app.
