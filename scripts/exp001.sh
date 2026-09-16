#!/usr/bin/env sh
set -eu
STORE_IP="$(kubectl -n shared-services get svc canary-store -o jsonpath='{.spec.clusterIP}')"
RUN_ID="exp001-$(date -u +%Y%m%dT%H%M%SZ)-$$"
CANARY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "run_id=$RUN_ID"
echo "[1/3] asserting direct tenant-a -> tenant-b pod IP is blocked"
B_IP="$(kubectl -n tenant-b get pod probe -o jsonpath='{.status.podIP}')"
if kubectl -n tenant-a exec probe -- curl --silent --show-error --max-time 2 "http://$B_IP:8080/" >/dev/null 2>&1; then
  echo "FAIL: direct cross-tenant connection unexpectedly succeeded" >&2; exit 1
fi
echo "PASS: direct cross-tenant probe was blocked"
echo "[2/3] writing synthetic canary from tenant-a through allowed shared service"
kubectl -n tenant-a exec probe -- curl --silent --show-error --fail --max-time 3 -X PUT --data-binary "$CANARY" "http://$STORE_IP:8080/v1/$RUN_ID"
echo
echo "[3/3] reading same canary from tenant-b through allowed shared service"
READ="$(kubectl -n tenant-b exec probe -- curl --silent --show-error --fail --max-time 3 "http://$STORE_IP:8080/v1/$RUN_ID")"
OBSERVED="$(printf '%s' "$READ" | python3 -c 'import json,sys; print(json.load(sys.stdin)["value"])')"
[ "$OBSERVED" = "$CANARY" ] || { echo "FAIL: exact canary not observed" >&2; exit 1; }
SHA="$(printf '%s' "$CANARY" | sha256sum | awk '{print $1}')"
echo "PASS: OBSERVED_REACHABLE"
echo "path=tenant-a/probe -> shared-services/canary-store -> tenant-b/probe"
echo "canary_sha256=$SHA"
