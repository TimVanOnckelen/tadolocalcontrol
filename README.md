# Tado Local Control - Home Assistant Add-on

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

![Project Maintenance][maintenance-shield]

A Home Assistant add-on that provides local control of Tado smart heating devices with a mobile-friendly web interface.

## About

This add-on creates a web interface for controlling your Tado heating devices directly through Home Assistant. It provides:

- 📱 Mobile-responsive web interface
- 🌡️ Real-time temperature control
- 🏠 Zone management
- 📅 Schedule management through Home Assistant automations
- 🔄 Real-time updates via WebSocket

## Installation

### Step 1: Add the Repository

1. In Home Assistant, navigate to **Settings** → **Add-ons**
2. Click the **Add-on Store** tab
3. Click the ⋮ menu in the top right corner
4. Select **Repositories**
5. Add this repository URL: `https://github.com/TimVanOnckelen/tadolocalcontrol`
6. Click **Add**

### Step 2: Install the Add-on

1. Refresh the Add-on Store page
2. Find **Tado Local Control** in the store
3. Click on it and then click **Install**
4. Wait for the installation to complete

### Step 3: Configure and Start

1. Go to the **Configuration** tab
2. Configure your settings (see Configuration section below)
3. Click **Save**
4. Go to the **Info** tab and click **Start**
5. Enable **Start on boot** if desired

## Configuration

### Basic Configuration

```yaml
entity_prefix: "tado_local"
log_level: "info"
auto_discover_zones: true
schedule_backup: true
```

### Configuration Options

| Option                | Type    | Default      | Description                                           |
| --------------------- | ------- | ------------ | ----------------------------------------------------- |
| `entity_prefix`       | string  | `tado_local` | Prefix for created entities                           |
| `log_level`           | list    | `info`       | Log level: `debug`, `info`, `warning`, or `error`     |
| `auto_discover_zones` | boolean | `true`       | Automatically discover Tado zones from Home Assistant |
| `schedule_backup`     | boolean | `true`       | Enable backup of schedule configurations              |

## Usage

1. After installation and starting the add-on, click **Open Web UI** or use the sidebar panel
2. Complete the initial setup by connecting to your Home Assistant instance
3. Select your Tado climate entities that you want to control
4. Use the mobile-friendly interface to control your heating zones

## Features

### Web Interface

- Clean, mobile-responsive design optimized for phones and tablets
- Real-time temperature display and control
- Quick temperature adjustment with +/- buttons
- Mode switching (auto/heat/off)
- Zone overview with current status
- Away/Home mode controls

### Home Assistant Integration

- Automatic discovery of existing Tado climate entities
- Real-time updates via WebSocket connection
- Schedule management through Home Assistant automations
- Integration with Home Assistant's away/home detection
- Persistent configuration storage

### API Endpoints

The add-on provides a REST API for advanced automation:

- `GET /api/zones` - List all configured zones
- `GET /api/zones/{entity_id}` - Get specific zone details
- `POST /api/zones/{entity_id}/temperature` - Set zone target temperature
- `POST /api/zones/{entity_id}/mode` - Set zone heating mode
- `GET /api/schedules` - List all schedules
- `POST /api/away-home/set` - Set away/home mode for all zones

## Troubleshooting

### Add-on Won't Start

Check the logs for specific error messages:

1. Go to the add-on's **Log** tab
2. Look for error messages during startup

Common issues:

- **Home Assistant API access**: Ensure the add-on has access to the Home Assistant API
- **Network connectivity**: Verify the add-on can reach your Home Assistant instance
- **Missing entities**: Make sure you have Tado climate entities in Home Assistant

### Can't Access Web Interface

1. Ensure the add-on is running (check the **Info** tab)
2. Try accessing via the direct URL: `http://homeassistant:8080`
3. Check if port 8080 is available and not blocked by firewall

### No Tado Entities Found

1. Verify your Tado integration is working in Home Assistant
2. Check that climate entities are available in **Developer Tools** → **States**
3. Entity names should follow the pattern: `climate.tado_*`

## Support

If you encounter issues:

1. Check the add-on logs first
2. Verify your Home Assistant and Tado integration are working
3. Search existing [issues][issues] for similar problems
4. Open a new issue with:
   - Add-on version
   - Home Assistant version
   - Relevant log entries
   - Steps to reproduce the problem

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE][license] file for details.

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/TimVanOnckelen/tadolocalcontrol.svg?style=for-the-badge
[commits]: https://github.com/TimVanOnckelen/tadolocalcontrol/commits/main
[license-shield]: https://img.shields.io/github/license/TimVanOnckelen/tadolocalcontrol.svg?style=for-the-badge
[license]: https://github.com/TimVanOnckelen/tadolocalcontrol/blob/main/LICENSE
[maintenance-shield]: https://img.shields.io/badge/maintainer-Tim%20Van%20Onckelen-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/TimVanOnckelen/tadolocalcontrol.svg?style=for-the-badge
[releases]: https://github.com/TimVanOnckelen/tadolocalcontrol/releases
[issues]: https://github.com/TimVanOnckelen/tadolocalcontrol/issues
