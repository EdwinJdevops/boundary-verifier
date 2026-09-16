IMAGE ?= boundary-verifier/canary-store:exp-001

.PHONY: image apply wait exp001 clean
image:
	docker build -f Dockerfile.canary-store -t $(IMAGE) .
apply:
	kubectl apply -f lab/kubernetes/00-namespaces.yaml
	kubectl apply -f lab/kubernetes/10-default-deny.yaml
	kubectl apply -f lab/kubernetes/11-default-deny-ingress.yaml
	kubectl apply -f lab/kubernetes/20-allow-shared-canary.yaml
	kubectl apply -f lab/kubernetes/30-canary-store.yaml
	kubectl apply -f lab/kubernetes/35-peer-endpoint.yaml
	kubectl apply -f lab/kubernetes/40-probes.yaml
wait:
	kubectl -n shared-services rollout status deployment/canary-store --timeout=120s
	kubectl -n tenant-a rollout status deployment/peer-endpoint --timeout=120s
	kubectl -n tenant-b rollout status deployment/peer-endpoint --timeout=120s
	kubectl -n tenant-a wait --for=condition=Ready pod/probe --timeout=120s
	kubectl -n tenant-b wait --for=condition=Ready pod/probe --timeout=120s
exp001:
	python3 scripts/run_exp001.py
clean:
	kubectl delete namespace tenant-a tenant-b shared-services --ignore-not-found
