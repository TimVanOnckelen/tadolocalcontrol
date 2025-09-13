# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- TBD

### Changed

- TBD

## [1.0.4] - 2025-09-13

### Fixed

- Fixed Home Assistant automation template errors with 'dict object has no attribute variables'
- Completely rewritten automation system to use individual automations per schedule entry
- Removed complex trigger variables that were causing template errors
- Simplified automation structure for better Home Assistant compatibility

### Changed

- Changed from single complex automation per zone to individual automations per schedule entry
- Improved automation naming and organization for better management
- Enhanced error handling in automation creation process

## [1.0.3] - 2025-09-13

### Fixed

- Fixed API URL paths for Home Assistant add-on ingress compatibility
- Changed all absolute API paths (/api/_) to relative paths (api/_) to work with HA proxy
- Improved Socket.IO configuration for Home Assistant add-on environment
- Added eventlet async mode and unsafe werkzeug support for better compatibility

### Changed

- Updated Socket.IO initialization to be more compatible with Home Assistant ingress
- Enhanced API routing to work correctly in both standalone and add-on modes

## [1.0.2] - 2025-09-13

### Fixed

- Fixed eventlet monkey patching issues causing runtime errors with gunicorn eventlet workers
- Fixed Home Assistant add-on configuration detection to prevent unnecessary setup redirects
- Resolved "Working outside of application context" errors during application startup

### Changed

- Added eventlet.monkey_patch() at the beginning of app.py before other imports
- Updated Config.is_configured() method to properly handle Home Assistant add-on environment
- Improved add-on integration to skip setup when running inside Home Assistant

## [1.0.1] - 2025-01-09

### Fixed

- Fixed Docker build issues with Python dependencies
- Removed unused aiohttp dependency that was causing build failures
- Fixed Dockerfile paths and permissions for add-on container
- Resolved config file conflicts with Home Assistant add-on structure
- Updated Python requirements for better compatibility

### Changed

- Moved application config from `config/` to `app_config/` to avoid conflicts
- Updated homeassistant_client.py to use requests instead of aiohttp
- Improved Dockerfile with proper error handling and optimizations
- Updated requirements.txt with compatible versions

## [1.0.0] - 2025-01-09

### Added

- Initial release
