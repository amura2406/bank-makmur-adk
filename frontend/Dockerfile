# ==========================================
# Stage 1: Build stage
# ==========================================
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies in a cached layer
COPY package*.json ./
RUN npm ci

# Copy application source code
COPY . .

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build Vite React app (outputs to /app/dist)
RUN npm run build

# ==========================================
# Stage 2: Production serve stage
# ==========================================
FROM nginx:1.25-alpine

# Copy custom Nginx configuration if SPA fallback is needed
# Otherwise default configuration serves /usr/share/nginx/html on port 80
COPY --from=build /app/dist /usr/share/nginx/html

COPY default.conf.template /etc/nginx/templates/default.conf.template

ENV PORT=8080
ENV NGINX_ENVSUBST_FILTER=PORT

# Expose port 8080 for production access
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
