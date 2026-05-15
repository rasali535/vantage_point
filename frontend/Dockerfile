# Build stage
FROM node:20-slim as build-stage

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Inject API URL during build if needed, or use relative paths
RUN npm run build

# Production stage
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
# Add custom nginx config for SPA routing if necessary
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass http://backend:8000; \
        proxy_read_timeout 120s; \
        proxy_connect_timeout 120s; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
