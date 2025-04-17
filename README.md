# NGINX Auth Gateway

This project sets up an NGINX API Gateway with a custom authentication validator service.

## Components

1. **NGINX Server**: Acts as the API Gateway and reverse proxy
   - Supports both open-source NGINX and NGINX Plus.
   - Optional integration with NGINX App Protect for enhanced security.
2. **Auth Validator Service**: A Flask application that validates request headers against an AWS Secret.
3. **Vault Integration**: Securely manages sensitive credentials using Ansible Vault.

## Setup Instructions

### Prerequisites

- Ansible 2.9+
- Target servers with SSH access
- Target servers with pre-installed packages or internet access
- NGINX Plus license files (if using NGINX Plus)
- AWS credentials for accessing Secrets Manager

### Securing Credentials

Before deployment, encrypt your AWS credentials and other sensitive data using Ansible Vault:

```bash
# Create encrypted vault
ansible-vault create inventory/group_vars/vault.yml

# Edit existing vault
ansible-vault edit inventory/group_vars/vault.yml
```

### Environment-Based Deployments

This project supports different environments (production, staging, development) with environment-specific configurations.

#### Available Environments

- `prod` (default): Production environment
- `staging`: Staging/testing environment
- `dev`: Development environment

You can find environment-specific configurations in the `environments/` directory.

#### Deployment

Deploy to a specific environment:

```bash
# Deploy to production (default)
ansible-playbook playbooks/master.yml --ask-vault-pass

# Deploy to staging
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=staging"

# Deploy to development
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=dev"
```

The `env` variable determines both:
1. Which environment configuration file to load (from `environments/<env>.yml`)
2. Which server group to target (from inventory - `[production]`, `[staging]`, or `[development]`)

#### Targeted Deployments

Deploy specific components using tags:

```bash
# Deploy only NGINX
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=staging" --tags "nginx"

# Deploy only validator service
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=dev" --tags "validator"

# Deploy setup components
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=prod" --tags "setup"
```

### NGINX Plus and App Protect

If using NGINX Plus and App Protect, ensure the following prerequisites are met:
- NGINX Plus license key and certificate files are available.
- App Protect WAF is enabled by setting `nginx_plus: true` in the environment configuration.
- App Protect policies can be customized in `roles/nginx/files/app-protect-policy.json`.

### Targeting Specific Servers

You can deploy to specific server groups defined in your inventory:

```bash
# Deploy to production servers
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=prod target_hosts=production"

# Deploy to staging servers
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=staging target_hosts=staging"

# Deploy to development servers
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=dev target_hosts=development"

# Deploy to a custom server group
ansible-playbook playbooks/master.yml --ask-vault-pass -e "env=prod target_hosts=custom_servers"
```

### Manual Component Deployment

Deploy components individually:

```bash
ansible-playbook playbooks/setup_users.yml -e "env=staging"
ansible-playbook playbooks/install_packages.yml -e "env=staging"
ansible-playbook playbooks/deploy_validator.yml -e "env=staging"
ansible-playbook playbooks/deploy_nginx.yml -e "env=staging"
```

## Variables Reference

This section describes all available variables used in the playbooks.

### AWS Authentication

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `aws_access_key_id` | AWS Access Key ID for Secrets Manager | N/A (Required) |
| `aws_secret_access_key` | AWS Secret Access Key for Secrets Manager | N/A (Required) |
| `aws_region` | AWS region where the secrets are stored | `eu-west-1` |
| `secret_name` | Name of the secret in AWS Secrets Manager | `secret/nginx/auth-validator` |

### Environment Settings

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `env` | Environment identifier used for logging and configuration | `prod` |
| `debug` | Enable debug logging in validator service | `false` |

### NGINX Configuration

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `nginx_plus` | Install NGINX Plus instead of open-source NGINX | `false` |
| `nginx_plus_license_key` | Path to NGINX Plus license key file | `""` |
| `nginx_plus_license_cert` | Path to NGINX Plus license certificate file | `""` |
| `nginx_plus_jwt_token` | Path to NGINX Plus JWT token file | `""` |
| `dns_servers` | DNS servers for NGINX to use for name resolution | `8.8.8.8 8.8.4.4` |
| `server_name` | NGINX server name directive | `aws-ingress-validator.local` |
| `server_port` | Port for NGINX to listen on | `443` |
| `server_health_check` | Enable health check endpoint | `false` |
| `server_health_check_path` | Path for health check endpoint | `/health` |
| `nginx_user` | User for NGINX processes | `nginx` |
| `nginx_group` | Group for NGINX processes | `nginx` |
| `nginx_cert_dir` | Directory for SSL certificates | `/etc/nginx/certs` |
| `nginx_pid_dir` | Directory for NGINX PID file | `/run/nginx` |

### Backend Configuration

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `backend_servers` | List of backend servers for proxying. Can be a simple list of server addresses or a list of objects with server configuration. | `[ - "localhost:8080"]` |

### SSL Configuration

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `create_self_signed_cert` | Whether to create a self-signed certificate | `true` |
| `server_certificate_chain` | Path to custom certificate chain file | `""` |
| `server_certificate_key` | Path to custom certificate key file | `""` |

### Validator Service Configuration

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `validator_user` | User for validator service | `auth-validator` |
| `validator_group` | Group for validator service | `auth-validator` |
| `validator_base_dir` | Base directory for validator service | `/opt/auth-validator` |
| `validator_log_dir` | Directory for validator logs | `/opt/auth-validator/logs` |
| `python_venv_dir` | Python virtual environment path | `/opt/auth-validator/venv` |
| `python_command` | Python interpreter command | `/usr/bin/python3` |
| `service_name` | Name of the validator systemd service | `auth-validator` |

## Testing

Test your API gateway with:

```bash
curl -X GET https://your-server/mock \
  -H 'Content-Type: application/json' \
  -H 'X-Secret-Header: YOUR_SECRET_VALUE' \
  -k -v
```

## Security Notes

- This setup uses TLS for all external communication.
- Authentication uses a secure header validated against AWS Secrets Manager.
- All secrets should be stored in an encrypted vault file.
- NGINX App Protect provides additional security features, including WAF policies.

## Automatic Service Restarts

The deployment playbooks automatically restart services when their configuration changes:

- When NGINX configuration files are modified, the NGINX service will be restarted.
- When Auth Validator configuration or Python code is modified, the validator service will be restarted.

This ensures that the latest configurations are always active without manual intervention.

### License

This project is licensed under the MIT License. See the `LICENSE` file for details.
