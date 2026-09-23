terraform {
  required_version = ">= 1.9"

  # State lives in a versioned bucket that this config creates (see main.tf, "Terraform
  # itself"). Bucket names can't be variables here; this one is ${project_id}-tfstate.
  backend "gcs" {
    bucket = "apelevate-cd6c73-tfstate"
    prefix = "apelevate"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  user_project_override = true
  billing_project       = var.project_id
}
