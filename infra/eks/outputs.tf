output "cluster_name" {
  value = aws_eks_cluster.exp001.name
}

output "cluster_arn" {
  value = aws_eks_cluster.exp001.arn
}

output "region" {
  value = var.aws_region
}

output "vpc_cni_version" {
  value = aws_eks_addon.vpc_cni.addon_version
}

output "node_instance_type" {
  value = var.node_instance_type
}
