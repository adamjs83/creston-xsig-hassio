# Crestron XSIG Integration for Home Assistant

[![Version](https://img.shields.io/badge/version-1.25.4-blue.svg)](https://github.com/adamjs83/creston-xsig-hassio/releases)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A comprehensive Home Assistant integration for Crestron control systems using the XSIG (External Signal) protocol. Control and monitor your Crestron devices directly from Home Assistant with full bidirectional communication.

## Why This Integration?

- **Complete UI Configuration** - Set up everything through the Home Assistant interface
- **No Coding Required** - Visual configuration for all entity types
- **Automatic YAML Import** - Seamlessly migrate from npope's original integration
- **Powerful Button Support** - Full keypad/dimmer support with LED feedback
- **Zero Restart Required** - Add, edit, or remove entities without restarting

## Topics

The full manual is split by topic; each file in `docs/` starts with a `Covers:` line and a `Last verified:` line.

| Topic | File | Covers |
|---|---|---|
| Features | [docs/features.md](docs/features.md) | Core capabilities, supported platforms, dimmer/keypad and advanced features. |
| Installation and quick start | [docs/installation.md](docs/installation.md) | HACS and manual install, first setup, migrating from npope's integration (quick start). |
| Configuration | [docs/configuration.md](docs/configuration.md) | UI configuration (entity and join management) and optional YAML configuration. |
| Dimmer and keypad configuration | [docs/dimmer-keypad.md](docs/dimmer-keypad.md) | Adding a dimmer/keypad, auto-sequential joins, created entities, button events, LED binding, Crestron-side programming. |
| Platform configuration | [docs/platforms.md](docs/platforms.md) | Light, switch, climate, cover, media player, sensor and binary sensor platforms. |
| Crestron programming | [docs/crestron-programming.md](docs/crestron-programming.md) | XSIG setup, separate XSIG symbols, join types and direction. |
| Troubleshooting | [docs/troubleshooting.md](docs/troubleshooting.md) | Debug logging and common issues. |
| Migration guide | [docs/migration.md](docs/migration.md) | Migrating from npope's original integration and from YAML to UI configuration. |
| Credits | [docs/credits.md](docs/credits.md) | Credits and enhancements in this fork. |

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Pull requests and issues welcome! Please test thoroughly before submitting.

## Links

- **GitHub:** https://github.com/adamjs83/creston-xsig-hassio
- **Original Integration:** https://github.com/npope/home-assistant-crestron-component
- **Home Assistant Docs:** https://www.home-assistant.io/docs/
- **Switch Manager:** https://github.com/Sian-Lee-SA/Home-Assistant-Switch-Manager
- **Issues:** https://github.com/adamjs83/creston-xsig-hassio/issues
