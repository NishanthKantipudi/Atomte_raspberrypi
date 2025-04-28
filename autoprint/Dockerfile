# FROM node:18-alpine AS builder
# WORKDIR /app
# COPY package*.json ./
# RUN npm install
# COPY . .
# COPY .env .env

# RUN npm run build

FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY ./build ./build
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
