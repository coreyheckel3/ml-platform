module "network" {
  source = "../../modules/network"

  project_name       = "forgeml"
  environment        = "staging"
  vpc_cidr           = "10.52.0.0/16"
  availability_zones = ["us-east-1a", "us-east-1b"]
}

