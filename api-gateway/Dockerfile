# Use official Go image
FROM golang:latest-alpine

# Set working directory
WORKDIR /app

# Copy go.mod and go.sum for caching
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest of the code
COPY . .

# Set Gin release mode
ENV GIN_MODE=release

# Expose HTTP port
EXPOSE 9000

# Build the binary
RUN go build -o gateway .

# Run the gateway
CMD ["./gateway"]