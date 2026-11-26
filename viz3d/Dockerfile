FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_USE_API_PROXY
ENV VITE_USE_API_PROXY=$VITE_USE_API_PROXY
RUN npm run build
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
