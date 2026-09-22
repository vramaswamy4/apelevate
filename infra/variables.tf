variable "project_id" {
  description = "Google Cloud project that hosts the demo."
  type        = string
}

variable "region" {
  description = "Cloud Run region. us-west1 (Oregon) sits next to the Neon database in AWS us-west-2."
  type        = string
  default     = "us-west1"
}

variable "billing_account" {
  description = "Billing account id, for the budget alert."
  type        = string
}

variable "github_repository" {
  description = "owner/name of the repository allowed to deploy."
  type        = string
  default     = "vramaswamy4/apelevate"
}

variable "image" {
  description = "Container image to run. CI deploys new images with gcloud; Terraform only sets the first one."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "monthly_budget_usd" {
  description = "Email alerts at 50%, 90% and 100% of this."
  type        = number
  default     = 5
}
