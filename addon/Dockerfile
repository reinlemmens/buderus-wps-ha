# Buderus WPS Heat Pump Add-on for Home Assistant
# Multi-architecture Docker build

ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-wheel

# Copy S6 overlay files first
COPY rootfs /

# Copy application code
COPY buderus_wps_addon /app/buderus_wps_addon

# Copy buderus_wps library (copied to addon/ during build)
COPY buderus_wps /app/buderus_wps
COPY buderus_wps_cli /app/buderus_wps_cli

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages \
    paho-mqtt>=2.0.0 \
    pyserial>=3.5

# Add app directory to Python path
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Set working directory
WORKDIR /app

# Labels for Home Assistant
LABEL \
    io.hass.name="Buderus WPS Heat Pump" \
    io.hass.description="Control Buderus WPS heat pumps via CAN bus over USB serial" \
    io.hass.type="addon" \
    io.hass.version="1.0.0"
