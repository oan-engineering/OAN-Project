#!/usr/bin/env bash
# Deploy a Crop Sown Registry build from ECR into the staging instance.
#
# The staging deploy IS the dev deploy — same chart, same images, same helm and
# kubectl fetching — under the staging release name. The two used to be separate
# copies of one helm command in the Jenkinsfile, and the copies drifted: when the
# dev deploy learned to fetch the helm the agent lacks, staging kept failing on
# "helm not found". So this sets the staging release and hands over to
# ci/deploy-dev.sh; see its header for every other variable.
#
# Which cluster it lands in is KUBECONFIG's call. In Jenkins that is the
# staging-rke2-kubeconfig credential, the RKE2 cluster on the staging EC2
# instance; by hand, point KUBECONFIG there first — the context is printed
# before anything is changed.
#
# Usage:
#   ./ci/deploy-staging.sh <tag>
#
#   AWS_ACCOUNT_ID=123456789012 KUBECONFIG=~/.kube/staging ./ci/deploy-staging.sh staging-7
#
# Env (beyond ci/deploy-dev.sh's):
#   STAGING_RELEASE    default cropsown-registry, as on dev — the
#                      openg2p-registry subchart rejects release names over 18
#                      characters
#   STAGING_NAMESPACE  default crop — the same name as dev; the kubeconfig, not
#                      the namespace, is what keeps the environments apart
set -euo pipefail

# Checked here rather than left to ci/deploy-dev.sh, whose usage line would name
# itself — and running that by hand would deploy the dev release name.
if [ -z "${1:-${TAG:-}}" ]; then
  echo "usage: $0 <tag>" >&2
  echo "   or: TAG=<tag> $0" >&2
  exit 2
fi

export RELEASE_NAME="${STAGING_RELEASE:-cropsown-registry}"
export NAMESPACE="${STAGING_NAMESPACE:-crop}"

exec "$(dirname "${BASH_SOURCE[0]}")/deploy-dev.sh" "$@"
