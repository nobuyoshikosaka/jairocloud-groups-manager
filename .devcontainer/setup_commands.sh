#!/bin/bash

install_deps() {
    # Install Python dependencies
    pip install --upgrade pip && pip install uv
    uv sync && uv pip install -e .

    # Install Node.js dependencies
    npm install -g npm && npm install -g pnpm
    pnpm config set global-bin-dir "$HOME/.local/bin"
    pnpm config set store-dir "$HOME/.pnpm-store"
    pnpm install
}


FUNCTION_NAME=$1

if [ -z "$FUNCTION_NAME" ]; then
    echo "Error: Function name argument is missing."
    exit 1
fi

shift

if type -t "$FUNCTION_NAME" | grep -q 'function'; then
    "$FUNCTION_NAME" "$@"
else
    echo "Error: Function '$FUNCTION_NAME' not found."
    exit 1
fi
