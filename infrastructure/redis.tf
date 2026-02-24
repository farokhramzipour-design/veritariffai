resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.name_prefix}-${var.environment}-redis-subnet"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_parameter_group" "redis7" {
  name   = "${var.name_prefix}-${var.environment}-redis7"
  family = "redis7"
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "${var.name_prefix}-${var.environment}-rg"
  description                   = "TCE Redis"
  engine                        = "redis"
  engine_version                = "7.0"
  port                          = 6379
  automatic_failover_enabled    = true
  transit_encryption_enabled    = true
  at_rest_encryption_enabled    = true
  parameter_group_name          = aws_elasticache_parameter_group.redis7.name
  subnet_group_name             = aws_elasticache_subnet_group.redis.name
  security_group_ids            = [aws_security_group.redis.id]
  maintenance_window            = "mon:03:00-mon:04:00"
  cluster_mode {
    replicas_per_node_group = 1
    num_node_groups         = 3
  }
  node_type = var.environment == "production" ? "cache.r6g.large" : "cache.t3.micro"
}
