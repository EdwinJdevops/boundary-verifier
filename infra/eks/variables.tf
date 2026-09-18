variable "aws_region" {
  description = "AWS region for the ephemeral EXP-001 reproduction."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Dedicated Boundary Verifier cluster name."
  type        = string
  default     = "boundary-verifier-exp001"
}

variable "kubernetes_version" {
  type    = string
  default = "1.36"
}

variable "vpc_cni_version" {
  type    = string
  default = "v1.22.4-eksbuild.3"
}

variable "node_instance_type" {
  type    = string
  default = "t3.medium"
}

variable "source_commit" {
  type = string
}
