variable "environment" {
  type    = string
  default = "staging"
}

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "name_prefix" {
  type    = string
  default = "tce"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "acm_certificate_arn" {
  type    = string
  default = ""
}
