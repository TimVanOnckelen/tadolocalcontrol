<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Tado Local Control Project

This project provides local control of Tado V3+ devices without relying on the Tado cloud API. It integrates with Home Assistant's HomeKit bridge to expose heating controls through HomeKit.

## Project Structure

- Python-based web application for Tado device communication
- Docker containerized deployment
- Simple web interface for mobile phone control
- Home Assistant integration for HomeKit bridge
- Local network communication with Tado devices
- Schedule and zone management capabilities

## Development Guidelines

- Focus on local network protocols and device discovery
- Implement secure communication with Tado devices
- Create responsive web UI for mobile control
- Provide clean integration with Home Assistant
- Follow HomeKit accessory patterns for device exposure
- Containerize application for easy deployment

## Technical Requirements

- Python web framework (Flask/FastAPI)
- Docker containerization
- Mobile-responsive web interface
- Local Tado V3+ device communication
- HomeKit integration via Home Assistant

- [x] Verify that the copilot-instructions.md file in the .github directory is created.
- [x] Clarify Project Requirements
- [x] Scaffold the Project
- [ ] Customize the Project
- [ ] Install Required Extensions
- [ ] Compile the Project
- [ ] Create and Run Task
- [ ] Launch the Project
- [ ] Ensure Documentation is Complete
