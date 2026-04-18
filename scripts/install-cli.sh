#!/usr/bin/env bash
set -euo pipefail

# MST CLI Installer
# Installs the mst command globally using pipx or uv tool install.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$(cd "$SCRIPT_DIR/../cli" && pwd)"

echo "Installing MST CLI from $CLI_DIR ..."

if command -v pipx &>/dev/null; then
    echo "Found pipx — installing with pipx..."
    pipx install "$CLI_DIR" --force
elif command -v uv &>/dev/null; then
    echo "Found uv — installing with uv tool..."
    uv tool install "$CLI_DIR" --force
else
    echo "Error: Neither pipx nor uv found."
    echo "Install one of:"
    echo "  brew install pipx   # or: python -m pip install --user pipx"
    echo "  brew install uv     # or: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Ensure ~/.local/bin is in PATH for both bash and zsh.
# uv tool update-shell only patches the current shell's profile,
# so we handle both explicitly.
UV_TOOL_BIN="$HOME/.local/bin"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
MARKER="# Added by MST CLI installer"

ensure_path_in_profile() {
    local profile="$1"
    if [[ -f "$profile" ]] && grep -qF '.local/bin' "$profile"; then
        return  # already present
    fi
    # Create the file if it doesn't exist (e.g. ~/.bashrc on a fresh macOS)
    echo "" >> "$profile"
    echo "$MARKER" >> "$profile"
    echo "$PATH_LINE" >> "$profile"
    echo "Updated $profile"
}

# bash: ~/.bashrc (interactive non-login) and ~/.bash_profile (login on macOS)
ensure_path_in_profile "$HOME/.bashrc"
if [[ "$(uname)" == "Darwin" ]]; then
    ensure_path_in_profile "$HOME/.bash_profile"
fi
# zsh: ~/.zshrc
ensure_path_in_profile "$HOME/.zshrc"

# Make mst available in the current shell session
if [[ ":$PATH:" != *":$UV_TOOL_BIN:"* ]]; then
    export PATH="$UV_TOOL_BIN:$PATH"
fi

echo ""
echo "✓ MST CLI installed! Run 'mst --help' to get started."
echo "  First-time setup: mst config init"
if ! command -v mst &>/dev/null; then
    echo ""
    echo "  Note: You may need to restart your shell or run:"
    echo "    source ~/.bashrc   # for bash"
    echo "    source ~/.zshrc    # for zsh"
fi
