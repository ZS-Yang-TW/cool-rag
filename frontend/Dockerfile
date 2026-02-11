FROM node:20-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build for development (with hot reload)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
