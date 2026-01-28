# syntax=docker/dockerfile:1

FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
RUN npm run build

# Determine build output folder (dist or build)
RUN if [ -d dist ]; then cp -r dist /tmp/app; \
    elif [ -d build ]; then cp -r build /tmp/app; \
    else echo "Build output folder not found (expected dist or build)" && exit 1; fi

FROM nginx:alpine
COPY --from=builder /tmp/app /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
