data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.1"

  name = "${var.name_prefix}-${var.environment}-vpc"
  cidr = var.vpc_cidr

  azs                 = slice(data.aws_availability_zones.available.names, 0, 2)
  public_subnets      = ["10.0.0.0/24", "10.0.1.0/24"]
  private_subnets     = ["10.0.10.0/24", "10.0.11.0/24"]
  enable_nat_gateway  = true
  single_nat_gateway  = false
  enable_dns_support  = true
  enable_dns_hostnames = true
}
