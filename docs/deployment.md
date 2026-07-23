# DMS Dokploy deployment

This directory owns the DMS deployment. It builds one image containing ERPNext,
Auto Service Management, HRMS, and Uganda Compliance; the existing Health
deployment remains separate.

## Manual image build gate

Run this command yourself from the DMS repository. It builds and pushes the
immutable image tag used by Dokploy; it does not change a running server.

```powershell
docker build --pull=false --progress=plain --tag aslamkimb/frappe-dms-ug:dev-31f2cae --file deployment/Containerfile .; if ($LASTEXITCODE -eq 0) { docker push aslamkimb/frappe-dms-ug:dev-31f2cae }
```

Use a new immutable tag for every later DMS commit. Do not use `latest`.

The image extends Frappe's immutable `version-16` build and runtime layers,
pinned by digest in `deployment/Containerfile`. Docker therefore downloads,
verifies, caches, and resumes those layers instead of rebuilding Python, Node,
wkhtmltopdf, Nginx, and Bench through fragile raw HTTP downloads.

The build uses clean committed snapshots from the four app repositories already
installed under `bench-data/bench-home/frappe-bench/apps`. It does not include
their working-tree changes or clone from GitHub inside Docker. The pinned source
revisions for this image are:

| App | Branch | Commit |
| --- | --- | --- |
| Frappe | `version-16` | `9a8daf343db69a0127f470bad8be0af192cd80c8` |
| ERPNext | `version-16` | `d1d3b241ae7bc21d18cf830a4bacd568e21a2a19` |
| HRMS | `version-16` | `6aa125b976469cb1c342afa3ef07d381c88677e0` |
| Uganda Compliance | `hotfix-v-16` | `33743cd596c6e8c079945478d0e5b52e461fe770` |

If one of those local repositories is missing or its `HEAD` has changed,
refresh the development stack and intentionally update the corresponding
commit argument before building a new immutable image tag.

## Dokploy configuration

Create a separate Dokploy Compose service from this repository and set its
Compose path to `deployment/docker-compose.dokploy.yml`. Add these values in
Dokploy Environment, never in a committed `.env` file:

```dotenv
DB_ROOT_PASSWORD=<new-unique-password>
ADMIN_PASSWORD=<new-unique-password>
SITE_NAME=<dms-domain>
CUSTOM_IMAGE=aslamkimb/frappe-dms-ug:dev-31f2cae
SOCKETIO_IMAGE=aslamkimb/frappe-dms-ug:dev-31f2cae
NGINX_IMAGE=aslamkimb/frappe-dms-ug:dev-31f2cae
```

In Dokploy Domains, route `<dms-domain>` to `frontend` on container port
`8080` using HTTP; Dokploy terminates TLS. Do not publish a host port or share
volumes, Redis, database, or site names with the Health deployment.

The app-install job enables site-level `developer_mode=1`, migrates, and clears
the cache on every deployment. Developer mode does not persist direct edits to
application code in the image layer: commit, rebuild, and redeploy code changes.

## Verification

After deployment, review the `create-site` and `install-apps` logs, then run
inside the backend container:

```bash
bench --site <dms-domain> list-apps
bench --site <dms-domain> show-config | grep developer_mode
bench --site <dms-domain> migrate
```

The app list must contain `frappe`, `erpnext`, `auto_service_management`,
`hrms`, and `uganda_compliance`. Verify Desk, Car Workshop, websocket,
customer portal, workers, scheduler, and a non-EFRIS billing flow. A repeat
deployment must preserve site data and complete without duplicate app installs.
