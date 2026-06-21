# Build context is the repo root (see docker-compose.prod.yml) so this can
# reach both frontend/ (build stage) and this directory's nginx.conf
# (final stage). One combined image: serves the built SPA and reverse
# proxies to Django -- sized for a single small VPS, not a multi-server
# topology.

FROM node:22-slim AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* /app/
RUN npm install

COPY frontend/ /app/

# Relative, not an absolute http://localhost:8000/... URL -- in production
# the SPA and API are same-origin behind this nginx container, unlike dev's
# cross-origin :5173 -> :8000 split (see frontend/src/api/client.ts).
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build


FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
