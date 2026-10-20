resource "cloudflare_pages_project" "this" {
  account_id        = var.account_id
  name              = var.domain_prefix
  production_branch = var.github_branch

  build_config = {
    build_command   = "npm run build"
    destination_dir = "dist"
  }

  source = {
    config = {
      production_deployments_enabled = true
      owner                          = var.github_owner
      production_branch              = var.github_branch
      repo_name                      = var.github_repo
    }
    type = "github"
  }
}

resource "cloudflare_zero_trust_access_identity_provider" "this" {
  config = {
    client_id     = var.google_client_id
    client_secret = var.google_client_secret
  }
  name       = "${var.name_prefix}-pages-google"
  type       = "google"
  account_id = var.account_id
}

resource "cloudflare_zero_trust_access_policy" "this" {
  account_id       = var.account_id
  decision         = "allow"
  name             = "${var.name_prefix}-pages-policy"
  session_duration = "168h"

  include = [
    for e in var.emails : {
      email = {
        email = e
      }
    }
  ]
}

resource "cloudflare_zero_trust_access_application" "this" {
  account_id       = var.account_id
  name             = "${var.name_prefix}-pages-access"
  domain           = cloudflare_pages_project.this.subdomain
  session_duration = "168h"
  type             = "self_hosted"
  allowed_idps     = [cloudflare_zero_trust_access_identity_provider.this.id]
  policies = [
    {
      id         = cloudflare_zero_trust_access_policy.this.id
      precedence = 1
    }
  ]
}

# As described here: https://github.com/cloudflare/terraform-provider-cloudflare/issues/3099
# creating or changing a pages project won't automatically deploy it, so we need to trigger the deployment manually
resource "terraform_data" "trigger_pages_deployment" {
  triggers_replace = [
    sha1(jsonencode({
      account_id        = var.account_id
      name              = var.domain_prefix
      production_branch = var.github_branch
      owner             = var.github_owner
      repo_name         = var.github_repo
    })),
  ]

  depends_on = [cloudflare_pages_project.this]

  provisioner "local-exec" {
    command = <<EOT
      curl -X POST "https://api.cloudflare.com/client/v4/accounts/${var.account_id}/pages/projects/${cloudflare_pages_project.this.name}/deployments" \
           -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
           -H "Content-Type: application/json" \
           --data '{"branch":"${var.github_branch}"}'
    EOT
    environment = {
      CLOUDFLARE_API_TOKEN = var.api_token
    }
  }
}

