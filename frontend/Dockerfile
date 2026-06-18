# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app

# Same-origin API path in production (Caddy proxies /api). Overridable.
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=$VITE_API_BASE

COPY package.json ./
# No lockfile is committed, so use install rather than ci.
RUN npm install
COPY . .
RUN npm run build

# ---- serve stage ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
