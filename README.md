# Tado Local Control

A local control application for Tado V3+ thermostats that bypasses the cloud API and integrates with Home Assistant for HomeKit control.

## Features

- **Local Communication**: Direct communication with Tado devices on your local network
- **Web Interface**: Mobile-responsive web app for device control
- **HomeKit Integration**: Exposes devices through Home Assistant's HomeKit bridge
- **Schedule Management**: Create and manage heating schedules
- **Zone Control**: Control multiple heating zones independently
- **Docker Support**: Containerized deployment for easy installation

## Quick Start

### Using Docker (Recommended)

```bash
# Build the image
docker build -t tado-local-control .

# Run the container
docker run -d \
  --name tado-control \
  --network host \
  -p 5000:5000 \
  -v $(pwd)/config:/app/config \
  tado-local-control
```

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## Configuration

Create a `config/config.yaml` file with your settings:

```yaml
tado:
  # Tado bridge IP will be auto-discovered if not specified
  bridge_ip: "192.168.1.100" # Optional

homeassistant:
  # Home Assistant integration settings
  base_url: "http://homeassistant:8123"
  token: "your_ha_token" # Optional

web:
  host: "0.0.0.0"
  port: 5000
  debug: false
```

## Home Assistant Integration

Add to your `configuration.yaml`:

```yaml
# Add this to expose through HomeKit
homekit:
  - name: Tado Local
    port: 21064
    filter:
      include_domains:
        - climate
      include_entities:
        - sensor.tado_*
        - climate.tado_*
```

## API Endpoints

- `GET /api/zones` - List all zones
- `GET /api/zones/{zone_id}` - Get zone details
- `POST /api/zones/{zone_id}/temperature` - Set target temperature
- `GET /api/schedules` - List all schedules
- `POST /api/schedules` - Create new schedule

## Web Interface

Access the web interface at `http://localhost:5000` for mobile control.

## License

MIT License
