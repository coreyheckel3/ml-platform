variable "aws_region" {
  type        = string
  description = "AWS region for the ForgeML development environment."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Project name used for resource naming and tags."
  default     = "forgeml"
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
  default     = "dev"
}

