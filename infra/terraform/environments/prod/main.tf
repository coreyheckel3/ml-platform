module "network" {
  source = "../../modules/network"

  project_name       = "forgeml"
  environment        = "prod"
  vpc_cidr           = "10.62.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

