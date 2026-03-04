#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_COMMAND=()

log() {
  printf '[install] %s\n' "$1"
}

warn() {
  printf '[install][warn] %s\n' "$1" >&2
}

die() {
  printf '[install][error] %s\n' "$1" >&2
  exit 1
}

run_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
    return
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return
  fi
  die "This step requires root privileges and sudo is not installed."
}

prompt_default() {
  local key="$1"
  local default_value="$2"
  local input
  read -r -p "$key [$default_value]: " input
  if [[ -z "${input}" ]]; then
    printf '%s\n' "$default_value"
    return
  fi
  printf '%s\n' "$input"
}

prompt_optional() {
  local key="$1"
  local input
  read -r -p "$key: " input
  printf '%s\n' "$input"
}

prompt_yes_no() {
  local key="$1"
  local default_value="$2"
  local input
  local normalized
  read -r -p "$key [$default_value]: " input
  input="${input:-$default_value}"
  normalized="$(printf '%s' "$input" | tr '[:upper:]' '[:lower:]')"
  case "$normalized" in
    y|yes) printf 'yes\n' ;;
    n|no) printf 'no\n' ;;
    *) die "Invalid answer for '$key'. Use yes or no." ;;
  esac
}

normalize_path_prefix() {
  local raw="$1"
  if [[ -z "$raw" || "$raw" == "/" ]]; then
    printf '/\n'
    return
  fi
  local prefixed="$raw"
  if [[ "${prefixed:0:1}" != "/" ]]; then
    prefixed="/$prefixed"
  fi
  prefixed="${prefixed%/}"
  printf '%s\n' "$prefixed"
}

build_api_prefix() {
  local app_prefix="$1"
  if [[ "$app_prefix" == "/" ]]; then
    printf '/api\n'
    return
  fi
  printf '%s/api\n' "$app_prefix"
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    die "Missing required command: $cmd"
  fi
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker CLI already available. Skipping Docker installation."
    return
  fi

  log "Docker CLI not found. Installing Docker engine and compose plugin."
  run_root apt-get update -y
  run_root apt-get install -y ca-certificates curl gnupg lsb-release git
  curl -fsSL https://get.docker.com | run_root sh
  run_root apt-get install -y docker-compose-plugin
  run_root systemctl enable --now docker
  warn "If your user is not in the docker group yet, run: sudo usermod -aG docker $USER and log in again."
}

ensure_git() {
  if command -v git >/dev/null 2>&1; then
    return
  fi
  log "Git not found. Installing git."
  run_root apt-get update -y
  run_root apt-get install -y git
}

ensure_python3() {
  if command -v python3 >/dev/null 2>&1; then
    return
  fi
  log "python3 not found. Installing python3."
  run_root apt-get update -y
  run_root apt-get install -y python3
}

detect_compose_command() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_COMMAND=(docker compose)
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_COMMAND=(docker-compose)
    return
  fi

  die "Neither 'docker compose' nor 'docker-compose' is available. Install Docker Compose and retry."
}

compose_cmd() {
  "${COMPOSE_COMMAND[@]}" -p "$STACK_NAME" --env-file "$DEPLOY_ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

render_template() {
  local template_file="$1"
  local target_file="$2"
  sed \
    -e "s|__DOMAIN__|$DOMAIN|g" \
    -e "s|__APP_PATH_PREFIX__|$APP_PATH_PREFIX|g" \
    -e "s|__API_URL_PREFIX__|$API_URL_PREFIX|g" \
    "$template_file" > "$target_file"
}

clone_or_update_repo() {
  if [[ -d "$REPO_DIR/.git" ]]; then
    log "Repository exists in $REPO_DIR. Pulling latest changes."
    git -C "$REPO_DIR" pull --ff-only || warn "Could not pull latest changes. Continuing with local checkout."
    return
  fi

  log "Cloning repository to $REPO_DIR"
  git clone "$REPO_URL" "$REPO_DIR"
}

resolve_optional_file_path() {
  local raw_path="$1"
  if [[ -z "$raw_path" ]]; then
    printf '\n'
    return
  fi
  if [[ "$raw_path" == ~/* ]]; then
    printf '%s/%s\n' "$HOME" "${raw_path#~/}"
    return
  fi
  printf '%s\n' "$raw_path"
}

apply_translation_replacements() {
  if [[ -z "$TRANSLATION_REPLACEMENT_FILE" ]]; then
    return
  fi

  if [[ ! -f "$TRANSLATION_REPLACEMENT_FILE" ]]; then
    die "Translation replacement file not found: $TRANSLATION_REPLACEMENT_FILE"
  fi

  ensure_python3

  local messages_file="$REPO_DIR/FE/src/core/i18n/messages.ts"
  if [[ ! -f "$messages_file" ]]; then
    die "Messages file not found: $messages_file"
  fi

  log "Applying translation replacements from $TRANSLATION_REPLACEMENT_FILE"
  python3 - "$TRANSLATION_REPLACEMENT_FILE" "$messages_file" <<'PY'
import json
import re
import sys


def load_pairs(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

  string_replacements = data.get("string_replacements", {})
  if string_replacements is None:
    string_replacements = {}
  if not isinstance(string_replacements, dict):
    raise SystemExit("'string_replacements' must be an object when provided.")

  key_replacements = data.get("key_replacements", {})
  if key_replacements is None:
    key_replacements = {}
  if not isinstance(key_replacements, dict):
    raise SystemExit("'key_replacements' must be an object when provided.")

  if not string_replacements and not key_replacements:
    raise SystemExit(
      "Replacement file must contain a non-empty 'string_replacements' or 'key_replacements' object."
    )

  pairs = []
  for old, new in string_replacements.items():
    if not isinstance(old, str) or not isinstance(new, str):
      raise SystemExit("All keys/values in 'string_replacements' must be strings.")
    pairs.append((old, new))

  normalized_key_replacements = {}
  for key_path, new_text in key_replacements.items():
    if not isinstance(key_path, str) or not isinstance(new_text, str):
      raise SystemExit("All keys/values in 'key_replacements' must be strings.")
    normalized_key_replacements[key_path] = new_text

  return pairs, normalized_key_replacements


def replace_in_single_quoted_literals(source: str, pairs):
    pattern = re.compile(r"'([^'\\]*(?:\\.[^'\\]*)*)'")

    def _replace(match):
        text = match.group(1)
        updated = text
        for old, new in pairs:
            updated = updated.replace(old, new)
        return f"'{updated}'"

    return pattern.sub(_replace, source)


  def escape_single_quoted(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


  def apply_key_replacements(source: str, key_replacements):
    if not key_replacements:
      return source

    lines = source.splitlines(keepends=True)
    updated_lines = []
    object_stack = []

    object_start_pattern = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\{\s*$")
    value_pattern = re.compile(
      r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*'((?:\\.|[^'\\])*)'(\s*,?\s*)$"
    )

    for line in lines:
      stripped = line.strip()

      if stripped.startswith("}") and object_stack:
        object_stack.pop()

      value_match = value_pattern.match(line)
      if value_match:
        indent, key, _existing, suffix = value_match.groups()
        full_path = ".".join(object_stack + [key])
        replacement = key_replacements.get(full_path)
        if replacement is not None:
          escaped_replacement = escape_single_quoted(replacement)
          line = f"{indent}{key}: '{escaped_replacement}'{suffix}"

      updated_lines.append(line)

      object_match = object_start_pattern.match(line)
      if object_match:
        object_stack.append(object_match.group(2))

    return "".join(updated_lines)


def main():
    replacement_path, messages_path = sys.argv[1], sys.argv[2]
  pairs, key_replacements = load_pairs(replacement_path)

    with open(messages_path, "r", encoding="utf-8") as handle:
        source = handle.read()

    updated = replace_in_single_quoted_literals(source, pairs)
    updated = apply_key_replacements(updated, key_replacements)

    with open(messages_path, "w", encoding="utf-8") as handle:
        handle.write(updated)


if __name__ == "__main__":
    main()
PY
}

build_frontend_artifact() {
  local image_tag="${STACK_NAME}-fe-build:latest"
  apply_translation_replacements
  log "Building frontend artifact image."
  docker build \
    -f "$REPO_DIR/FE/Dockerfile.build" \
    --build-arg "VITE_APP_TITLE=$APP_TITLE" \
    --build-arg "VITE_APP_PROFILE=production" \
    --build-arg "VITE_PUBLIC_BASE_PATH=$FRONTEND_BASE_PATH" \
    --build-arg "VITE_API_BASE_URL=$API_URL_PREFIX" \
    -t "$image_tag" \
    "$REPO_DIR/FE"

  rm -rf "$FRONTEND_DIST_DIR"
  mkdir -p "$FRONTEND_DIST_DIR"

  local container_id
  container_id="$(docker create "$image_tag")"
  docker cp "$container_id:/app/dist/." "$FRONTEND_DIST_DIR"
  docker rm "$container_id" >/dev/null
  log "Frontend artifact ready in $FRONTEND_DIST_DIR"
}

request_letsencrypt_certificate() {
  log "Requesting/renewing Let's Encrypt certificate for $DOMAIN"
  docker run --rm \
    -v "${STACK_NAME}_letsencrypt_data:/etc/letsencrypt" \
    -v "${STACK_NAME}_certbot_www:/var/www/certbot" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --domain "$DOMAIN" \
    --email "$LETSENCRYPT_EMAIL" \
    --agree-tos \
    --non-interactive \
    --keep-until-expiring
}

build_cors_origins() {
  if [[ "$DOMAIN" == "localhost" ]]; then
    printf 'http://localhost,http://127.0.0.1\n'
    return
  fi
  printf 'http://%s,https://%s\n' "$DOMAIN" "$DOMAIN"
}

main() {
  ensure_git
  ensure_docker
  require_command docker
  detect_compose_command

  local default_repo_url
  default_repo_url="https://github.com/niels/TiMa.git"
  if git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    default_repo_url="$(git -C "$SCRIPT_DIR" remote get-url origin 2>/dev/null || printf '%s' "$default_repo_url")"
  fi

  REPO_URL="$(prompt_default "Repository URL" "$default_repo_url")"
  INSTALL_ROOT="$(prompt_default "Install root directory" "$HOME/tima-deploy")"
  STACK_NAME="$(prompt_default "Docker stack name" "tima")"
  DOMAIN="$(prompt_default "Domain (or localhost)" "localhost")"
  APP_PATH_PREFIX="$(normalize_path_prefix "$(prompt_default "App path prefix" "/tima")")"
  APP_TITLE="$(prompt_default "Browser tab title" "TiMa")"
  TRANSLATION_REPLACEMENT_FILE_RAW="$(prompt_optional "Translation replacement JSON file (optional)")"
  USE_OWN_NGINX="$(prompt_yes_no "Use your own nginx instance" "no")"

  ENABLE_LETSENCRYPT="no"
  LETSENCRYPT_EMAIL=""
  if [[ "$USE_OWN_NGINX" == "no" && "$DOMAIN" != "localhost" ]]; then
    ENABLE_LETSENCRYPT="$(prompt_yes_no "Enable Let's Encrypt + certbot" "no")"
    if [[ "$ENABLE_LETSENCRYPT" == "yes" ]]; then
      LETSENCRYPT_EMAIL="$(prompt_default "Let's Encrypt email" "admin@$DOMAIN")"
    fi
  fi

  APP_PATH_PREFIX="$(normalize_path_prefix "$APP_PATH_PREFIX")"
  API_URL_PREFIX="$(build_api_prefix "$APP_PATH_PREFIX")"
  TRANSLATION_REPLACEMENT_FILE="$(resolve_optional_file_path "$TRANSLATION_REPLACEMENT_FILE_RAW")"
  if [[ "$APP_PATH_PREFIX" == "/" ]]; then
    FRONTEND_BASE_PATH='/'
  else
    FRONTEND_BASE_PATH="$APP_PATH_PREFIX/"
  fi

  REPO_DIR="$INSTALL_ROOT/repository"
  DEPLOY_DIR="$INSTALL_ROOT/deploy"
  FRONTEND_DIST_DIR="$INSTALL_ROOT/artifacts/frontend-dist"
  NGINX_RUNTIME_DIR="$DEPLOY_DIR/nginx"
  DEPLOY_ENV_FILE="$DEPLOY_DIR/.env"
  COMPOSE_FILE="$REPO_DIR/deploy/docker-compose.rpi.yml"

  mkdir -p "$INSTALL_ROOT" "$DEPLOY_DIR" "$NGINX_RUNTIME_DIR"
  clone_or_update_repo

  if [[ "$USE_OWN_NGINX" == "yes" ]]; then
    NGINX_CONF_FILE="$NGINX_RUNTIME_DIR/manual-nginx-snippet.conf"
    render_template "$REPO_DIR/deploy/nginx/http.conf.template" "$NGINX_CONF_FILE"
  else
    NGINX_CONF_FILE="$NGINX_RUNTIME_DIR/default.conf"
    if [[ "$ENABLE_LETSENCRYPT" == "yes" ]]; then
      render_template "$REPO_DIR/deploy/nginx/http.conf.template" "$NGINX_CONF_FILE"
    else
      render_template "$REPO_DIR/deploy/nginx/http.conf.template" "$NGINX_CONF_FILE"
    fi
  fi

  MOSQUITTO_CONFIG_DIR="$REPO_DIR/mosquitto"
  CORS_ALLOWED_ORIGINS="$(build_cors_origins)"

  cat > "$DEPLOY_ENV_FILE" <<EOF
STACK_NAME=$STACK_NAME
REPO_DIR=$REPO_DIR
MOSQUITTO_CONFIG_DIR=$MOSQUITTO_CONFIG_DIR
FRONTEND_DIST_DIR=$FRONTEND_DIST_DIR
NGINX_CONF_FILE=$NGINX_CONF_FILE
API_URL_PREFIX=$API_URL_PREFIX
CORS_ALLOWED_ORIGINS=$CORS_ALLOWED_ORIGINS
TRANSLATION_REPLACEMENT_FILE=$TRANSLATION_REPLACEMENT_FILE
EOF

  build_frontend_artifact

  if [[ "$USE_OWN_NGINX" == "yes" ]]; then
    log "Starting backend + mosquitto only (nginx skipped by choice)."
    compose_cmd up -d mosquitto backend
    log "Deployment completed."
    printf '\n'
    printf 'Frontend artifact: %s\n' "$FRONTEND_DIST_DIR"
    printf 'Manual nginx snippet: %s\n' "$NGINX_CONF_FILE"
    printf 'Backend API prefix: %s\n' "$API_URL_PREFIX"
    exit 0
  fi

  log "Starting full stack with nginx."
  compose_cmd up -d mosquitto backend nginx

  if [[ "$ENABLE_LETSENCRYPT" == "yes" ]]; then
    request_letsencrypt_certificate
    render_template "$REPO_DIR/deploy/nginx/https.conf.template" "$NGINX_CONF_FILE"
    compose_cmd up -d nginx
    log "HTTPS enabled via Let's Encrypt."
  fi

  log "Deployment completed."
  printf '\n'
  printf 'Frontend URL path: %s\n' "$APP_PATH_PREFIX/"
  printf 'API URL path: %s\n' "$API_URL_PREFIX"
  printf 'Nginx config: %s\n' "$NGINX_CONF_FILE"
}

main "$@"
