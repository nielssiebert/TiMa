# Raspberry Pi Docker Deployment

This deployment bundle installs TiMa (Mosquitto + Flask backend + Vue frontend) on a fresh Raspberry Pi using Docker, with optional nginx and optional Let's Encrypt.

## What is included

- `install.sh` (idempotent installer with interactive prompts)
- `deploy/docker-compose.rpi.yml` (runtime stack)
- `TiMa/Dockerfile` (backend image)
- `FE/Dockerfile.build` (frontend build artifact image)
- `deploy/nginx/*.template` (nginx reverse-proxy configs)
- `deploy/translation-replacements.valve.example.json` (example translation replacement file)

## Security defaults

- nginx reverse proxies backend and is the single entry point.
- SSL/TLS can be enabled with Let's Encrypt + certbot.

## Install

1. Copy `install.sh` to your Raspberry Pi (or run it from this repository).
2. Make it executable:

```bash
chmod +x install.sh
```

3. Run:

```bash
./install.sh
```

The script checks if Docker CLI exists and skips Docker installation if available.

## Interactive options

The script prompts for:

- repository URL to clone
- installation directory
- docker stack name
- domain (`localhost` or custom domain)
- app path prefix (example: `/tima`)
- browser tab title (used for frontend build)
- optional translation replacement JSON file (applied to frontend messages at deployment build time)
- whether to use your own nginx
- whether to enable Let's Encrypt (if nginx is managed by script)

## Translation replacements at deployment time

The installer can apply string replacements to `FE/src/core/i18n/messages.ts` before the frontend build.

It also supports exact key-based text overrides for dotted translation paths (for example `en.entities.sequences.fields.executionEvents`).

Use this for renaming terms such as:

- `ExecutionEvent` → `Valve`
- `ExecutionEventGroup` → `ValveGroup`

Expected JSON format:

```json
{
	"string_replacements": {
		"ExecutionEventGroup": "ValveGroup",
		"ExecutionEvent": "Valve",
		"execution events": "valves",
		"execution event": "valve"
	},
	"key_replacements": {
		"en.entities.sequences.fields.executionEvents": "Valves",
		"en.entities.sequences.fields.executionEventGroups": "ValveGroups"
	}
}
```

An example file is provided at `deploy/translation-replacements.valve.example.json`.

## Own nginx mode

If you choose your own nginx instance:

- nginx container is not deployed
- frontend build artifacts are still generated
- script outputs a ready-to-adapt nginx snippet in your deploy folder
- backend + mosquitto are started by Docker Compose

## Paths and outputs

Default install root: `$HOME/tima-deploy`

Generated runtime assets:

- repository clone: `$HOME/tima-deploy/repository`
- frontend dist: `$HOME/tima-deploy/artifacts/frontend-dist`
- runtime nginx conf/snippet: `$HOME/tima-deploy/deploy/nginx`
- docker env file: `$HOME/tima-deploy/deploy/.env`

## Re-running after failures

The installer is designed to be re-runnable:

- existing repository is updated with `git pull`
- frontend artifact is rebuilt
- compose uses `up -d` for idempotent start/update
- certbot runs with `--keep-until-expiring`

## Path prefix behavior

Example with `/tima` prefix:

- frontend served under `/tima/`
- backend API under `/tima/api`

This allows multiple apps behind one host/port.

## SQLite persistence

SQLite lives in a Docker named volume (`tima_sqlite`) mapped to backend path `/data/tima.sqlite`.

## Resource profile

Compose sets per-container memory limits for lower RAM usage on Raspberry Pi:

- mosquitto: 64 MB
- backend: 256 MB
- nginx: 96 MB

Adjust limits in `deploy/docker-compose.rpi.yml` if needed.
