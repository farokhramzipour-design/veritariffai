module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.5"

  identifier = "${var.name_prefix}-${var.environment}-db"
  engine     = "postgres"
  engine_version = "16.3"
  instance_class = var.environment == "production" ? "db.r6g.large" : "db.t3.medium"
  allocated_storage = 100
  db_name   = "tce"
  username  = "master"
  manage_master_user_password = true
  multi_az  = var.environment == "production" ? true : false
  skip_final_snapshot = true
  vpc_security_group_ids = [aws_security_group.rds.id]
  subnet_ids = module.vpc.private_subnets
}
