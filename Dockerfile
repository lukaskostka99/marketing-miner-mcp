FROM node:20-slim

WORKDIR /app

# Kopíruj package files
COPY package.json tsconfig.json ./

# Instaluj dependencies
RUN npm install

# Kopíruj source code
COPY src/ ./src/

# Build TypeScript
RUN npm run build

# Spusť server
CMD ["npm", "start"]
