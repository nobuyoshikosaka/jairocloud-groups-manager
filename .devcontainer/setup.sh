#!/bin/bash
set -e

REMOTE_USER=$1
BASHRC_FILE="/home/${REMOTE_USER}/.bashrc"

if [ -z "$REMOTE_USER" ]; then
    echo "Error: User name argument is missing."
    exit 1
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


if [ -S /var/run/docker.sock ]; then
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)

    EXISTING_GROUP=$(getent group "$DOCKER_GID" | cut -d: -f1)
    if [ -n "$EXISTING_GROUP" ] && [ "$EXISTING_GROUP" != "docker" ]; then
        FOUND_GID=""
        for NEW_GID in $(seq 998 -1 1); do
            if ! getent group $NEW_GID > /dev/null; then
                FOUND_GID=$NEW_GID
                break
            fi
        done

        if [ -z "$FOUND_GID" ]; then
            for NEW_GID in $(seq 10000 11000); do
                if ! getent group $NEW_GID > /dev/null; then
                    FOUND_GID=$NEW_GID
                    break
                fi
            done
        fi

        if [ -n "$FOUND_GID" ]; then
            sudo groupmod -g $FOUND_GID "$EXISTING_GROUP"
        else
            echo "Error: No available GID found to resolve group conflict." >&2
            exit 1
        fi
    fi

    if getent group docker > /dev/null 2>&1; then
        sudo groupmod -g $DOCKER_GID docker
    else
        sudo groupadd -g $DOCKER_GID docker
    fi
    sudo usermod -aG docker "${REMOTE_USER}"

    if ! grep -q "docker_reload" "$BASHRC_FILE" 2>/dev/null; then
        {
        echo ""
        echo "# docker_reload"
        echo "if ! groups | grep -q 'docker'; then"
        echo "  exec newgrp docker"
        echo "fi"
        } >> "$BASHRC_FILE"

        sudo chown ${REMOTE_USER}:${REMOTE_USER} "$BASHRC_FILE"
    fi
fi
