#!/bin/bash
set -e

REMOTE_USER=$1
BASHRC_FILE="/home/${REMOTE_USER}/.bashrc"

if [ -z "$REMOTE_USER" ]; then
    echo "Error: User name argument is missing."
    exit 1
fi

if [ -S /var/run/docker.sock ]; then
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)

    sudo groupadd -g $DOCKER_GID docker_host || true
    sudo usermod -aG docker_host "${REMOTE_USER}"

    if ! grep -q "docker_host_reload" "$BASHRC_FILE" 2>/dev/null; then
        {
        echo ""
        echo "# docker_host_reload"
        echo "if ! groups | grep -q 'docker_host'; then"
        echo "  exec newgrp docker_host"
        echo "fi"
        } >> "$BASHRC_FILE"

        sudo chown ${REMOTE_USER}:${REMOTE_USER} "$BASHRC_FILE"
    fi
fi

if ! grep -q "venv_activate_reload" "$BASHRC_FILE" 2>/dev/null; then
    {
    echo ""
    echo "# venv_activate_reload"
    echo "if [ -f /home/${REMOTE_USER}/.venv/bin/activate ]; then"
    echo "  source /home/${REMOTE_USER}/.venv/bin/activate"
    echo "fi"
    } >> "$BASHRC_FILE"

    sudo chown ${REMOTE_USER}:${REMOTE_USER} "$BASHRC_FILE"
fi


pip install --upgrade pip
pip install uv && uv sync

npm install -g pnpm
pnpm config set store-dir "$HOME/.pnpm-store"
pnpm install
