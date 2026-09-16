#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-boundary-verifier-exp001}"
KIND_NODE_IMAGE="${KIND_NODE_IMAGE:-kindest/node:v1.35.8@sha256:07b2536e30b803ed61d1677a79df6115f798ce64c80f9e22f6ed45afd09323c0}"
CALICO_COMMIT="${CALICO_COMMIT:-db255c554b929afd73552fd3ac81d691107a1607}"
IMAGE="${IMAGE:-boundary-verifier/canary-store:exp-001}"

cleanup() {
  if [[ "${KEEP_CLUSTER:-0}" != "1" ]]; then
    kind delete cluster --name "$CLUSTER_NAME" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

diagnostics() {
  local rc=$?
  if [[ $rc -eq 0 ]]; then
    return 0
  fi
  set +e
  echo "::group::EXP-001 failure diagnostics"
  kubectl get nodes -o wide
  kubectl get pods -A -o wide
  for ns in shared-services tenant-a tenant-b; do
    echo "===== namespace: $ns ====="
    kubectl -n "$ns" get all -o wide
    kubectl -n "$ns" get events --sort-by=.lastTimestamp
    kubectl -n "$ns" describe pods
    for pod in $(kubectl -n "$ns" get pods -o name 2>/dev/null); do
      kubectl -n "$ns" logs "$pod" --all-containers --tail=200 2>/dev/null || true
    done
  done
  echo "::endgroup::"
  return $rc
}
trap diagnostics ERR

kind create cluster --name "$CLUSTER_NAME" --image "$KIND_NODE_IMAGE" --config lab/kind/exp001.yaml --wait 120s

CALICO_URL="https://raw.githubusercontent.com/projectcalico/calico/$CALICO_COMMIT/manifests/calico.yaml"
curl --fail --silent --show-error --location "$CALICO_URL" --output /tmp/calico.yaml
kubectl apply -f /tmp/calico.yaml
kubectl -n kube-system rollout status daemonset/calico-node --timeout=240s
kubectl -n kube-system rollout status deployment/calico-kube-controllers --timeout=240s
kubectl wait --for=condition=Ready nodes --all --timeout=240s

docker build --pull -f Dockerfile.canary-store -t "$IMAGE" .
kind load docker-image "$IMAGE" --name "$CLUSTER_NAME"

# Bring up endpoints before policy. This lets the experiment prove that later
# failures are caused by isolation rather than dead destinations.
kubectl apply -f lab/kubernetes/00-namespaces.yaml
kubectl apply -f lab/kubernetes/30-canary-store.yaml
kubectl apply -f lab/kubernetes/35-peer-endpoint.yaml
kubectl apply -f lab/kubernetes/40-probes.yaml

kubectl -n shared-services rollout status deployment/canary-store --timeout=120s
kubectl -n tenant-a rollout status deployment/peer-endpoint --timeout=120s
kubectl -n tenant-b rollout status deployment/peer-endpoint --timeout=120s
kubectl -n tenant-a wait --for=condition=Ready pod/probe --timeout=120s
kubectl -n tenant-b wait --for=condition=Ready pod/probe --timeout=120s

A_IP="$(kubectl -n tenant-a get svc peer-endpoint -o jsonpath='{.spec.clusterIP}')"
B_IP="$(kubectl -n tenant-b get svc peer-endpoint -o jsonpath='{.spec.clusterIP}')"
STORE_IP="$(kubectl -n shared-services get svc canary-store -o jsonpath='{.spec.clusterIP}')"
kubectl -n tenant-a exec probe -- curl --silent --show-error --fail --max-time 3 "http://$B_IP:8080/healthz" >/dev/null
kubectl -n tenant-b exec probe -- curl --silent --show-error --fail --max-time 3 "http://$A_IP:8080/healthz" >/dev/null
kubectl -n tenant-a exec probe -- curl --silent --show-error --fail --max-time 3 "http://$STORE_IP:8080/healthz" >/dev/null
kubectl -n tenant-b exec probe -- curl --silent --show-error --fail --max-time 3 "http://$STORE_IP:8080/healthz" >/dev/null

# Only after reachability is proven do we introduce the declared isolation.
kubectl apply -f lab/kubernetes/10-default-deny.yaml
kubectl apply -f lab/kubernetes/11-default-deny-ingress.yaml
kubectl apply -f lab/kubernetes/20-allow-shared-canary.yaml
kubectl apply -f lab/kubernetes/21-allow-canary-ingress.yaml

python3 scripts/run_exp001.py
