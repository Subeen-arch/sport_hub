# Project support files

The active application remains in the root `frontend/` and `backend/` directories. Shared documentation and launch utilities remain in `docs/` and `scripts/`.

This folder groups supporting material without deleting the originals' contents:

- `legacy-uploads/`: original files previously in root `uploaded_img/`. These are reference assets, not database imports or files served by the new application.
- `reference-images/`: the directory previously named `project images/`, retained for project references (currently empty).
- `deployment/`: Docker Compose configuration and the production environment template previously at the root.

Active frontend images remain in `frontend/public/images/`. The hidden root `.tools/`, `.venv/`, and `.runtime/` folders remain in place because installed tools, the Python environment, launch scripts, and the local PostgreSQL cluster depend on those locations. `.gitignore`, `.htaccess`, and the main README also remain at root.

## Deployment paths

Create the private `project-support/deployment/.env.production` from the adjacent `.env.production.example` and supply deployment-specific values. From the repository root, the Compose command is:

```powershell
docker compose --env-file project-support/deployment/.env.production -f project-support/deployment/compose.yaml up --build -d
```

Build paths are relative to the relocated Compose file and still point to the root applications. Named database/media volumes retain their existing names through `name: sporthub-next`. `DJANGO_SECURE_COOKIES` supplies both Django session and CSRF cookie flags.

The production cutover gate is still open: HTTPS termination, trusted proxy behavior, security checks, backup/restore procedures, and an actual deployment must be verified before public launch. These file moves do not deploy the application.

Local development continues to use `scripts/start.ps1` from the repository root. No existing file was deleted during this reorganization. The move-time SHA-256 manifest is kept locally in ignored `.runtime/project-reorganization.json`; deployment configuration was subsequently updated for its new location.
