FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .
RUN npm run build

# Production stage: nginx serves the built assets as a non-root user
FROM nginxinc/nginx-unprivileged:1.25-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/conf.d/security-headers.conf

EXPOSE 8765

CMD ["nginx", "-g", "daemon off;"]
