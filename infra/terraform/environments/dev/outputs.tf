output "vpc_id" {
  description = "ForgeML development VPC ID."
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs for platform workloads."
  value       = module.network.private_subnet_ids
}

