# CryptoAudit website (static React build behind nginx, proxying /api to the API container).
# Build from the repository root: docker build -f docker/web.Dockerfile -t cryptoaudit-web .
FROM node:22-alpine AS build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM nginx:1.27-alpine
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 80
