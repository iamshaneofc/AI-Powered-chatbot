# ===========================================================================
# Frontend Dockerfile — Multi-stage build for production
# ===========================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build the React application
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first for layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Build the application using Vite
# We accept an API URL arg to embed during build time
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Serve the application with Nginx
# ---------------------------------------------------------------------------
FROM nginx:alpine AS runtime

# Copy custom Nginx configuration if you have one, or just use the default
# COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Nginx runs automatically when container starts
CMD ["nginx", "-g", "daemon off;"]
