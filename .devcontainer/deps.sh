pip install --upgrade pip
pip install uv && uv sync

npm install -g npm && npm install -g pnpm
pnpm config set store-dir "$HOME/.pnpm-store"
pnpm install
