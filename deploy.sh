#!/bin/bash
set -e
echo "[deploy.sh] Starting deployment of $APP_NAME..."

# ── Backend (Python/FastAPI) ──
echo "[deploy.sh] Installing backend..."
cd "$APP_DIR/backend"
python3 -m venv venv 2>/dev/null || true
. venv/bin/activate
pip install -r requirements.txt -q 2>&1 | tail -3

# Create .env for backend
cat > "$APP_DIR/backend/.env" << ENVEOF
DATABASE_URL=postgresql://preview_admin:previewPass2026!@$DB_HOST:5432/$DB_NAME
REDIS_URL=redis://:previewRedis2026!@$DB_HOST:6380
SECRET_KEY=$(openssl rand -hex 16)
ALLOWED_ORIGINS=*
DEBUG=false
ENVEOF

# ── Frontends (Vite/React) ──
FPORT=$FRONTEND_PORT
for dir in $APP_DIR/frontend*; do
  [ -d "$dir" ] || continue
  DIRNAME=$(basename "$dir")
  echo "[deploy.sh] Installing $DIRNAME..."
  cd "$dir"
  npm install -q 2>&1 | tail -3

  # Write vite.config.ts
  cat > "$dir/vite.config.ts" << 'VEOF'
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: {
    port: FPORT_PLACEHOLDER,
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: { '/api': { target: 'http://localhost:BPORT_PLACEHOLDER', changeOrigin: true } },
  },
});
VEOF
  sed -i "s/FPORT_PLACEHOLDER/$FPORT/" "$dir/vite.config.ts"
  sed -i "s/BPORT_PLACEHOLDER/$BACKEND_PORT/" "$dir/vite.config.ts"

  FPORT=$((FPORT + 1))
done

# ── PM2 Ecosystem ──
echo "[deploy.sh] Creating PM2 config..."
APPS="["
# Backend
APPS="$APPS{\"name\":\"${PM2_PREFIX}-backend\",\"cwd\":\"$APP_DIR/backend\",\"script\":\"venv/bin/uvicorn\",\"args\":\"app.main:app --host 0.0.0.0 --port $BACKEND_PORT\",\"interpreter\":\"$APP_DIR/backend/venv/bin/python3\",\"max_restarts\":10}"

# Celery worker (if exists)
if grep -rl "celery" "$APP_DIR/backend/" >/dev/null 2>&1; then
  APPS="$APPS,{\"name\":\"${PM2_PREFIX}-worker\",\"cwd\":\"$APP_DIR/backend\",\"script\":\"venv/bin/celery\",\"args\":\"-A app.core.celery_app worker --loglevel=info\",\"interpreter\":\"$APP_DIR/backend/venv/bin/python3\",\"max_restarts\":10}"
fi

# Frontends
FPORT=$FRONTEND_PORT
for dir in $APP_DIR/frontend*; do
  [ -d "$dir" ] || continue
  DIRNAME=$(basename "$dir")
  APPS="$APPS,{\"name\":\"${PM2_PREFIX}-${DIRNAME}\",\"cwd\":\"$dir\",\"script\":\"npx\",\"args\":\"vite\",\"max_restarts\":10}"
  FPORT=$((FPORT + 1))
done

APPS="$APPS]"
echo "module.exports = {apps: $APPS};" > "$APP_DIR/ecosystem.config.js"

# ── Database migrations ──
echo "[deploy.sh] Running migrations..."
cd "$APP_DIR/backend"
. venv/bin/activate
python3 -c "from app.core.database import engine; from app.models import *; import asyncio; asyncio.run(engine.dispose())" 2>/dev/null || echo "No auto-migration"

# ── Seed data ──
if [ -f "$APP_DIR/Makefile" ] && grep -q "seed" "$APP_DIR/Makefile"; then
  echo "[deploy.sh] Running seed via Makefile..."
  cd "$APP_DIR" && make seed 2>&1 | tail -5 || true
fi

# ── Start PM2 ──
echo "[deploy.sh] Starting services..."
cd "$APP_DIR"
pm2 start ecosystem.config.js 2>&1
pm2 save 2>/dev/null || true

echo "[deploy.sh] Done!"
