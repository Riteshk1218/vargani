# Build the website, then serve it with nginx (which also forwards /api to Django).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# The site configuration (deploy/nginx.conf) is mounted by docker-compose.prod.yml.
EXPOSE 80
