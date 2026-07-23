module "network" {
  source = "../../modules/network"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = "10.42.0.0/16"
  availability_zones = ["${var.aws_region}a", "${var.aws_region}b"]
}

