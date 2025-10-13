# Security Policy

## Implemented Security Features

This application includes several security measures to protect against common vulnerabilities:

### 1. Environment-based Configuration
- **Secret Key**: Flask secret key is now stored in environment variables instead of hardcoded in source
- **Configuration File**: All sensitive settings moved to `.env` file (not tracked in git)
- See `env.example` for configuration template

### 2. SSRF Protection
- **URL Validation**: All URLs are validated before fetching
- **Private IP Blocking**: Blocks access to:
  - Private networks (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
  - Localhost (127.0.0.1, ::1, localhost)
  - Link-local addresses
- **Domain Whitelisting**: Optional whitelist for allowed domains
- **Protocol Validation**: Only HTTP/HTTPS protocols allowed

### 3. XXE Attack Prevention
- **defusedxml**: Uses `defusedxml` library instead of standard `xml.etree.ElementTree`
- Protects against XML External Entity (XXE) attacks
- Prevents XML bomb attacks

### 4. Resource Limits
- **File Size Limit**: Configurable maximum XML file size (default: 10MB)
- **Timeout Protection**: Configurable HTTP request timeout
- **Streaming Download**: Downloads are streamed and size-checked incrementally

### 5. Systemd Security Hardening
The systemd service file includes multiple security features:
- Runs as `www-data` user (not root)
- `NoNewPrivileges=true` - prevents privilege escalation
- `PrivateTmp=true` - isolated /tmp directory
- `ProtectSystem=strict` - read-only /usr and /boot
- `ProtectHome=true` - no access to /home
- `ProtectKernelTunables=true` - kernel protection
- `RestrictNamespaces=true` - namespace restrictions

### 6. Dependency Management
- All dependencies are pinned to specific versions
- Regular updates recommended for security patches

## Reporting a Vulnerability

If you discover a security vulnerability, please email: [your-email@example.com]

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Security Checklist for Production

Before deploying to production, ensure:

- [ ] `.env` file exists with unique `SECRET_KEY`
- [ ] `SECRET_KEY` is a strong random string (use `python3 -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] `FLASK_ENV=production` is set
- [ ] `DEBUG=False` is set
- [ ] `ALLOWED_DOMAINS` is configured (if applicable)
- [ ] Application runs as `www-data` user (not root)
- [ ] `.env` file has restrictive permissions (640)
- [ ] SSL/TLS is configured (HTTPS)
- [ ] Firewall rules are properly configured
- [ ] Regular backups are configured
- [ ] Logs are monitored

## Updates and Patches

- Check for updates regularly: `git pull origin main`
- Update dependencies: `pip install -r requirements.txt --upgrade`
- Review `env.example` for new configuration options
- Restart service after updates: `sudo systemctl restart feedcompare`

## Secure Defaults

The application uses secure defaults:
- Debug mode OFF in production
- Request timeout: 30 seconds
- Max file size: 10MB
- HTTPS/HTTP only protocols

However, these can be customized via `.env` file as needed.

