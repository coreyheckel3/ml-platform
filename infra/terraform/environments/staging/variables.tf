variable "aws_region" {
  type        = string
  description = "AWS region for the ForgeML staging environment."
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
  default     = "staging"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the staging VPC."
  default     = "10.52.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "Availability zones used for staging public and private subnets."
  default     = ["us-east-1a", "us-east-1b"]
}
