module "ecs_cluster" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "~> 5.3"

  cluster_name = "${var.name_prefix}-${var.environment}-ecs"
}
