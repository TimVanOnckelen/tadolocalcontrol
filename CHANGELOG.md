# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- TBD

### Changed
- TBD

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
