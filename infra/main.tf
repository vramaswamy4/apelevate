# The public demo on Google Cloud: Cloud Run (web + jobs), a private bucket for uploads,
# Secret Manager, a nightly reset, keyless deploys from GitHub Actions, and a budget alert.
# The database is Neon Postgres (outside Google Cloud); its URL lives in Secret Manager.

data "google_project" "this" {}

locals {
  service_name = "apelevate"
  # Cloud Run's deterministic URL, known before the service exists, so ALLOWED_HOSTS can be set.
  service_host = "${local.service_name}-${data.google_project.this.number}.${var.region}.run.app"
  apis = [
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# ---------- Images ---------------------------------------------------------------------------

resource "google_artifact_registry_repository" "images" {
  repository_id = "apelevate"
  location      = var.region
  format        = "DOCKER"
  description   = "APElevate container images, pushed by CI."

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }
  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      older_than = "604800s" # 7 days
    }
  }

  depends_on = [google_project_service.apis]
}

# ---------- Runtime identity, secrets, storage ----------------------------------------------

resource "google_service_account" "runtime" {
  account_id   = "apelevate-run"
  display_name = "APElevate runtime (Cloud Run service and jobs)"
}

resource "random_password" "django_secret_key" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "django_secret_key" {
  secret_id = "django-secret-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "django_secret_key" {
  secret      = google_secret_manager_secret.django_secret_key.id
  secret_data = random_password.django_secret_key.result
}

# The Neon connection string. Terraform creates the empty secret; the value is added by hand
# (gcloud secrets versions add database-url --data-file=-) so it never sits in Terraform state.
resource "google_secret_manager_secret" "database_url" {
  secret_id = "database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_iam_member" "runtime_reads" {
  for_each = {
    django = google_secret_manager_secret.django_secret_key.id
    db     = google_secret_manager_secret.database_url.id
  }
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket" "private_uploads" {
  name                        = "${var.project_id}-private-uploads"
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  # Demo data resets nightly; nothing here needs to outlive a few days.
  lifecycle_rule {
    condition {
      age = 3
    }
    action {
      type = "Delete"
    }
  }
  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "runtime_objects" {
  bucket = google_storage_bucket.private_uploads.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

# ---------- The web service and its jobs ----------------------------------------------------

locals {
  plain_env = {
    DJANGO_DEBUG                = "0"
    DJANGO_SECURE               = "1"
    DJANGO_ALLOWED_HOSTS        = local.service_host
    DJANGO_CSRF_TRUSTED_ORIGINS = "https://${local.service_host}"
    DEMO_MODE                   = "1"
    PAYMENTS_BACKEND            = "fake"
    PRIVATE_STORAGE_BUCKET      = google_storage_bucket.private_uploads.name
    WEB_CONCURRENCY             = "2"
  }
  secret_env = {
    DJANGO_SECRET_KEY = google_secret_manager_secret.django_secret_key.secret_id
    DATABASE_URL      = google_secret_manager_secret.database_url.secret_id
  }
}

resource "google_cloud_run_v2_service" "web" {
  name                = local.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.runtime.email
    scaling {
      min_instance_count = 0 # scale to zero: the demo costs nothing while nobody is looking
      max_instance_count = 2
    }
    containers {
      image = var.image
      ports {
        container_port = 8000
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      dynamic "env" {
        for_each = local.plain_env
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
    }
  }

  # CI deploys new images; Terraform owns everything else about the service.
  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }

  depends_on = [google_secret_manager_secret_iam_member.runtime_reads]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.web.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "task" {
  for_each = {
    migrate = ["python", "manage.py", "migrate", "--noinput"]
    reset   = ["python", "manage.py", "reset_demo"]
  }
  name                = "apelevate-${each.key}"
  location            = var.region
  deletion_protection = false

  template {
    template {
      service_account = google_service_account.runtime.email
      max_retries     = 1
      timeout         = "600s"
      containers {
        image   = var.image
        command = each.value
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
        dynamic "env" {
          for_each = local.plain_env
          content {
            name  = env.key
            value = env.value
          }
        }
        dynamic "env" {
          for_each = local.secret_env
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }

  depends_on = [google_secret_manager_secret_iam_member.runtime_reads]
}

# ---------- Nightly reset -------------------------------------------------------------------

resource "google_service_account" "scheduler" {
  account_id   = "apelevate-scheduler"
  display_name = "Runs the nightly demo reset"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_runs_reset" {
  name     = google_cloud_run_v2_job.task["reset"].name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "nightly_reset" {
  name      = "apelevate-nightly-reset"
  region    = var.region
  schedule  = "0 8 * * *" # 08:00 UTC = midnight/1am in California
  time_zone = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.task["reset"].name}:run"
    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
  depends_on = [google_project_service.apis]
}

# ---------- Keyless deploys from GitHub Actions ---------------------------------------------

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub OIDC"
  # Only this repository's workflows can get a token.
  attribute_condition = "assertion.repository == '${var.github_repository}'"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deployer" {
  account_id   = "apelevate-deployer"
  display_name = "GitHub Actions deployer"
}

resource "google_service_account_iam_member" "github_impersonates_deployer" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_project_iam_member" "deployer" {
  for_each = toset(["roles/run.developer", "roles/artifactregistry.writer"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.deployer.email}"
}

# Deploying a service or job that runs as the runtime account requires acting as it.
resource "google_service_account_iam_member" "deployer_acts_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

# ---------- Budget alert --------------------------------------------------------------------

resource "google_billing_budget" "demo" {
  billing_account = var.billing_account
  display_name    = "APElevate demo"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }
  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }
  depends_on = [google_project_service.apis]
}
