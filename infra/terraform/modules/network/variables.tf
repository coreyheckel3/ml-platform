variable "project_name" {
  type        = string
  description = "Project name used for resource tags."
}

variable "environment" {
  type        = string
  description = "Environment name."
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the environment VPC."
}

variable "availability_zones" {
  type        = list(string)
  description = "Availability zones used for public and private subnets."
}

