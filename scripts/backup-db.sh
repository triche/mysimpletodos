#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# backup-db.sh — Back up and restore the MySimpleTodos SQLite database
#
# Commands:
#   backup  [DEST]   Copy the DB from the container (default: backups/todo-<timestamp>.db)
#   restore <FILE>   Copy a backup into the container and restart it
#   list             List all backups in the backups/ directory
#
# Options:
#   -h, --help       Show this help message
# ---------------------------------------------------------------------------

CONTAINER="mysimpletodos-app"
SERVICE="todo-app"
REMOTE_DB="/data/todo.db"
BACKUP_DIR="./backups"

usage() {
    cat <<EOF
Usage: $(basename "$0") <command> [options]

Commands:
  backup  [DEST]   Back up the database from the running container.
                   Default destination: ${BACKUP_DIR}/todo-YYYY-MM-DD-HHMMSS.db
  restore <FILE>   Restore a backup file into the container and restart.
  list             List available backups in ${BACKUP_DIR}/.

Options:
  -h, --help       Show this help message and exit.
EOF
}

require_container() {
    if ! docker compose ps --status running --format '{{.Name}}' 2>/dev/null | grep -q "$CONTAINER"; then
        echo "Error: container '$CONTAINER' is not running." >&2
        echo "Start it with:  docker compose up -d" >&2
        exit 1
    fi
}

cmd_backup() {
    local dest="${1:-}"
    if [[ -z "$dest" ]]; then
        mkdir -p "$BACKUP_DIR"
        local stamp
        stamp=$(date +%Y-%m-%d-%H%M%S)
        dest="${BACKUP_DIR}/todo-${stamp}.db"
    fi

    require_container
    echo "Backing up ${SERVICE}:${REMOTE_DB} → ${dest}"
    docker compose cp "${SERVICE}:${REMOTE_DB}" "$dest"
    echo "Backup saved: ${dest} ($(du -h "$dest" | cut -f1))"
}

cmd_restore() {
    local src="${1:-}"
    if [[ -z "$src" ]]; then
        echo "Error: restore requires a backup file path." >&2
        echo "Usage: $(basename "$0") restore <FILE>" >&2
        exit 1
    fi
    if [[ ! -f "$src" ]]; then
        echo "Error: file not found: ${src}" >&2
        exit 1
    fi

    require_container
    echo "Restoring ${src} → ${SERVICE}:${REMOTE_DB}"
    docker compose cp "$src" "${SERVICE}:${REMOTE_DB}"
    echo "Restarting container…"
    docker compose restart "$SERVICE"
    echo "Restore complete."
}

cmd_list() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        echo "No backups directory found (${BACKUP_DIR})."
        return
    fi

    local files
    files=$(find "$BACKUP_DIR" -maxdepth 1 -name '*.db' -type f 2>/dev/null | sort)
    if [[ -z "$files" ]]; then
        echo "No backups found in ${BACKUP_DIR}/."
        return
    fi

    printf "%-40s  %s\n" "FILE" "SIZE"
    printf "%-40s  %s\n" "----" "----"
    while IFS= read -r f; do
        printf "%-40s  %s\n" "$f" "$(du -h "$f" | cut -f1)"
    done <<< "$files"
}

# --- Main dispatch ---------------------------------------------------------

cmd="${1:-}"

case "$cmd" in
    backup)  shift; cmd_backup "$@" ;;
    restore) shift; cmd_restore "$@" ;;
    list)    cmd_list ;;
    -h|--help|help) usage ;;
    "")
        echo "Error: no command specified." >&2
        usage >&2
        exit 1
        ;;
    *)
        echo "Error: unknown command '${cmd}'." >&2
        usage >&2
        exit 1
        ;;
esac
