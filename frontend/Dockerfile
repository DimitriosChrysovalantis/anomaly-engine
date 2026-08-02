# Use a lightweight Node.js image
FROM node:22-alpine

# Set the working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Expose the Vite development port
EXPOSE 5173

# Start the Vite server and expose it to the Docker network
CMD ["npm", "run", "dev", "--", "--host"]