output "vpc_id" {
  description = "ForgeML staging VPC ID."
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for staging ingress resources."
  value       = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private subnet IDs for staging platform workloads."
  value       = module.network.private_subnet_ids
}
