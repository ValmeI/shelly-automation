#!/bin/bash
# Deploy Shelly Automation to homelab server
# Can be run standalone or called from homelab/deploy.sh

set -euo pipefail

# --- Configuration ---
REMOTE_HOST="${HOMELAB_HOST:-homelab.local}"
SSH_KEY="${HOMELAB_SSH_KEY:-$HOME/.ssh/id_homelab}"
REMOTE_APP_DIR="/opt/shelly-automation"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false

# --- Logging ---
_ts() { date '+%Y-%m-%d %H:%M:%S'; }
log()         { echo "$(_ts)  $*"; }
log_success() { echo "$(_ts)  OK: $*"; }
log_error()   { echo "$(_ts)  ERROR: $*" >&2; }
log_warning() { echo "$(_ts)  WARN: $*"; }

# --- Remote execution helpers ---
remote_exec() {
    local cmd="$1"
    local log_msg="${2:-}"

    if [[ "$DRY_RUN" == true ]]; then
        [[ -n "$log_msg" ]] && log "$log_msg"
        echo "[DRY RUN] Would execute: $cmd"
        return 0
    fi

    [[ -n "$log_msg" ]] && log "$log_msg"
    ssh -i "$SSH_KEY" "$REMOTE_HOST" "$cmd"
}

remote_exec_sudo() {
    local cmd="$1"
    local log_msg="${2:-}"

    if [[ "$DRY_RUN" == true ]]; then
        [[ -n "$log_msg" ]] && log "$log_msg"
        echo "[DRY RUN] Would execute (sudo): $cmd"
        return 0
    fi

    [[ -n "$log_msg" ]] && log "$log_msg"
    ssh -i "$SSH_KEY" "$REMOTE_HOST" "sudo $cmd"
}

remote_copy() {
    local src="$1"
    local dst="$2"

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] Would copy: $src -> $REMOTE_HOST:$dst"
        return 0
    fi

    scp -i "$SSH_KEY" "$src" "$REMOTE_HOST:$dst"
}

# --- Usage ---
usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deploy Shelly Automation to homelab server.

OPTIONS:
    -h, --help       Show this help message
    -n, --dry-run    Show what would be deployed without applying
    --host HOST      Override remote host (default: homelab.local)
EOF
    exit 0
}

# --- Argument parsing ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        -n|--dry-run) DRY_RUN=true; shift ;;
        --host) REMOTE_HOST="$2"; shift 2 ;;
        *) log_error "Unknown option: $1"; usage ;;
    esac
done

# --- Main deployment ---
log "Deploying Shelly Automation to $REMOTE_HOST..."

# Preflight checks
if [[ ! -f "$SSH_KEY" ]]; then
    log_error "SSH key not found: $SSH_KEY"
    exit 1
fi

if [[ "$DRY_RUN" != true ]]; then
    if ! ssh -i "$SSH_KEY" -o ConnectTimeout=5 "$REMOTE_HOST" "true" 2>/dev/null; then
        log_error "Cannot connect to $REMOTE_HOST"
        exit 1
    fi
    log_success "SSH connectivity OK"
fi

# Ensure atd is installed and running
if ! remote_exec "systemctl is-active atd" > /dev/null 2>&1; then
    log "Installing and enabling atd daemon..."
    remote_exec_sudo "apt-get update && sudo apt-get install -y at"
    remote_exec_sudo "systemctl enable --now atd"
fi
log_success "atd daemon is running"

# Clone repository if not exists
if ! remote_exec "test -d $REMOTE_APP_DIR/.git" > /dev/null 2>&1; then
    log "Cloning shelly-automation repository..."
    remote_exec_sudo "git clone https://github.com/ValmeI/shelly-automation $REMOTE_APP_DIR"
    remote_exec_sudo "chown -R valme:valme $REMOTE_APP_DIR"
fi

# Pull latest code
if ! remote_exec "cd $REMOTE_APP_DIR && git pull" \
    "Pulling latest code from GitHub..."; then
    log_error "Failed to pull - fix conflicts on server first"
    exit 1
fi
log_success "Code updated from GitHub"

# Setup Python venv if not exists
if ! remote_exec "test -d $REMOTE_APP_DIR/.venv" > /dev/null 2>&1; then
    log "Creating Python virtual environment..."
    remote_exec "cd $REMOTE_APP_DIR && python3 -m venv .venv"
    remote_exec "cd $REMOTE_APP_DIR && source .venv/bin/activate && pip install --upgrade pip"
fi

# Install/update dependencies
remote_exec "cd $REMOTE_APP_DIR && source .venv/bin/activate && pip install -r requirements.txt" \
    "Installing Python dependencies..."
log_success "Dependencies installed"

# Deploy runtime script
remote_copy "$SCRIPT_DIR/run_scheduler.sh" "/tmp/run_scheduler.sh"
remote_exec_sudo "cp /tmp/run_scheduler.sh $REMOTE_APP_DIR/run_scheduler.sh"
remote_exec_sudo "chmod +x $REMOTE_APP_DIR/run_scheduler.sh"
remote_exec_sudo "chown valme:valme $REMOTE_APP_DIR/run_scheduler.sh"
remote_exec "rm -f /tmp/run_scheduler.sh"
log_success "Runtime script deployed"

# Deploy config
if [[ ! -f "$SCRIPT_DIR/config.yaml" ]]; then
    log_error "Config not found: $SCRIPT_DIR/config.yaml"
    log "Copy config.yaml.example to config.yaml and configure it"
    exit 1
fi

remote_copy "$SCRIPT_DIR/config.yaml" "/tmp/shelly_config.yaml"
remote_exec_sudo "cp /tmp/shelly_config.yaml $REMOTE_APP_DIR/config.yaml"
remote_exec_sudo "chmod 600 $REMOTE_APP_DIR/config.yaml"
remote_exec_sudo "chown valme:valme $REMOTE_APP_DIR/config.yaml"
remote_exec "rm -f /tmp/shelly_config.yaml"
log_success "Config deployed"

# Create logs directory
remote_exec "mkdir -p $REMOTE_APP_DIR/logs"

# Add cron job if not exists (daily at 00:01)
if ! remote_exec "crontab -l 2>/dev/null | grep -q 'shelly-automation/run_scheduler.sh'"; then
    remote_exec "(crontab -l 2>/dev/null; echo -e '\n# Shelly Automation - schedule light on/off jobs daily at 00:01\n1 0 * * * $REMOTE_APP_DIR/run_scheduler.sh > /dev/null 2>&1') | crontab -" \
        "Adding cron job (daily at 00:01)..."
    log_success "Cron job added"
else
    log_success "Cron job already exists"
fi

# Run scheduler once to test and schedule today's jobs
log "Running scheduler to set up today's jobs..."
if remote_exec "$REMOTE_APP_DIR/run_scheduler.sh" 2>/dev/null; then
    log_success "Today's jobs scheduled successfully"
    remote_exec "atq" || true
else
    log_warning "Could not schedule today's jobs (check config and device connectivity)"
fi

log_success "Shelly Automation deployed successfully"
