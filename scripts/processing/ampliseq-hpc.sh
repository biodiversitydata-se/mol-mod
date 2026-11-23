#!/bin/bash
# Run nf-core/ampliseq taxonomic annotation for a dataset on the HPC cluster.
# Run from the dataset folder, after ampliseq-config-generator.R has written
# ampliseq/params.yaml and section 11 of asv-input-processing.R has written
# output/<datasetID>.fasta.
#
# Usage: ampliseq-hpc.sh push|start|status|fetch [-f]
#   push    create the remote dataset folder and copy params.yaml and the fasta
#   start   start ampliseq in a detached screen session on the login node
#           (log in run.log; always with -resume, so it also continues a
#           failed or interrupted run)
#   status  show the screen session, the end of run.log and whether
#           annotation.tsv exists
#   fetch   copy results/SBDI/annotation.tsv to input/annotation.tsv
#           (-f to overwrite an existing file), plus the DADA2 taxonomy
#           tables results/dada2/ASV_tax.*.tsv if present (used to check
#           the PR2 genus/species corrections). ampliseq writes these when
#           classifying with DADA2, so there are none for SINTAX (COI) runs.
#
# Defaults are for Dardel (PDC). Settings can be overridden with environment
# variables; paths on the cluster are relative to the remote home directory:
#   AMPLISEQ_CONFIG_DIR     local folder with params.yaml (default: ampliseq)
#   AMPLISEQ_SSH_HOST       ssh host for commands (default: dardel)
#   AMPLISEQ_TRANSFER_HOST  ssh host for file transfer (default: dardel-ft)
#   AMPLISEQ_REMOTE_DIR     parent folder of dataset folders
#                           (default: SBDI/asv-portal/initial-annotations)
#   AMPLISEQ_NXF_ENV        shared Nextflow environment file
#                           (default: SBDI/asv-portal/nxf_env)
#   AMPLISEQ_MODULES        modules to load
#                           (default: PDC nextflow/25.10.4 apptainer java/17)
#   AMPLISEQ_PROFILE        Nextflow profile (default: pdc_kth)
set -euo pipefail

config_dir="${AMPLISEQ_CONFIG_DIR:-ampliseq}"
ssh_host="${AMPLISEQ_SSH_HOST:-dardel}"
transfer_host="${AMPLISEQ_TRANSFER_HOST:-dardel-ft}"
remote_parent="${AMPLISEQ_REMOTE_DIR:-SBDI/asv-portal/initial-annotations}"
nxf_env="${AMPLISEQ_NXF_ENV:-SBDI/asv-portal/nxf_env}"
modules="${AMPLISEQ_MODULES:-PDC nextflow/25.10.4 apptainer java/17}"
profile="${AMPLISEQ_PROFILE:-pdc_kth}"

usage() {
  sed -n '7,18p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

[[ $# -ge 1 ]] || usage
cmd="$1"
force="${2:-}"

params="$config_dir/params.yaml"
[[ -f "$params" ]] || { echo "Error: $params not found. Run from the dataset folder, after ampliseq-config-generator.R." >&2; exit 1; }

# Dataset ID and ampliseq version, as written by ampliseq-config-generator.R
fasta_name="$(sed -n 's/^input_fasta: *"\(.*\)"$/\1/p' "$params")"
dataset_id="${fasta_name%.fasta}"
version="$(sed -n 's/^# ampliseq_version: *//p' "$params")"
[[ "$dataset_id" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Error: unexpected input_fasta in $params: '$fasta_name'" >&2; exit 1; }
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Error: no valid '# ampliseq_version:' line in $params" >&2; exit 1; }

remote_dir="$remote_parent/$dataset_id"
ssh_opts=(-o ConnectTimeout=20)

case "$cmd" in
  push)
    fasta="output/$fasta_name"
    [[ -f "$fasta" ]] || { echo "Error: $fasta not found (run section 11 of asv-input-processing.R)" >&2; exit 1; }
    if ssh "${ssh_opts[@]}" "$ssh_host" "test -d '$remote_dir/results'"; then
      echo "Warning: $remote_dir/results already exists on $ssh_host; start will resume that run." >&2
    fi
    ssh "${ssh_opts[@]}" "$ssh_host" "mkdir -p '$remote_dir'"
    scp "${ssh_opts[@]}" "$params" "$fasta" "$transfer_host:$remote_dir/"
    echo "Copied params.yaml and $fasta_name to $ssh_host:$remote_dir"
    ;;

  start)
    ssh "${ssh_opts[@]}" "$ssh_host" bash -l -s <<EOF
set -euo pipefail
cd '$remote_dir' 2>/dev/null || { echo "Error: $remote_dir not found; run push first" >&2; exit 1; }
for f in params.yaml '$fasta_name'; do
  [[ -f "\$f" ]] || { echo "Error: \$f missing in $remote_dir; run push first" >&2; exit 1; }
done
[[ -f ~/'$nxf_env' ]] || { echo "Error: ~/$nxf_env not found" >&2; exit 1; }
if screen -ls | grep -q '[.]$dataset_id[[:space:]]'; then
  echo "Error: a screen session '$dataset_id' is already running (screen -r $dataset_id)" >&2
  exit 1
fi
# All output, including module load notices, goes to run.log
screen -dmS '$dataset_id' bash -lc "{ module load $modules && source ~/'$nxf_env' && nextflow run nf-core/ampliseq -r $version -profile $profile -params-file params.yaml -resume; } > run.log 2>&1"
sleep 2
screen -ls | grep '[.]$dataset_id[[:space:]]' || { echo "Error: screen session did not start" >&2; exit 1; }
# Screen sessions only exist on the login node they were started on
hostname > .ampliseq_login_node
echo "Started ampliseq $version for $dataset_id in screen session '$dataset_id' on \$(hostname)."
echo "Follow with: ampliseq-hpc.sh status   (or on \$(hostname): screen -r $dataset_id)"
EOF
    ;;

  status)
    ssh "${ssh_opts[@]}" "$ssh_host" bash -l -s <<EOF
cd '$remote_dir' 2>/dev/null || { echo "$remote_dir not found on $ssh_host" >&2; exit 1; }
start_node=\$(cat .ampliseq_login_node 2>/dev/null || echo unknown)
if [[ "\$start_node" != unknown && "\$start_node" != "\$(hostname)" ]]; then
  echo "Screen session '$dataset_id': unknown (started on \$start_node, this is \$(hostname)); see run.log"
elif screen -ls | grep -q '[.]$dataset_id[[:space:]]'; then
  echo "Screen session '$dataset_id': running on \$(hostname)"
else
  echo "Screen session '$dataset_id': not running"
fi
if [[ -f results/SBDI/annotation.tsv ]]; then
  echo "results/SBDI/annotation.tsv: present (\$(wc -l < results/SBDI/annotation.tsv) lines)"
else
  echo "results/SBDI/annotation.tsv: not yet present"
fi
if [[ -f run.log ]]; then
  echo "--- end of run.log"
  tail -n 15 run.log
fi
EOF
    ;;

  fetch)
    target="input/annotation.tsv"
    if [[ -f "$target" && "$force" != "-f" ]]; then
      echo "Error: $target already exists; use 'fetch -f' to overwrite" >&2
      exit 1
    fi
    mkdir -p input
    scp "${ssh_opts[@]}" "$transfer_host:$remote_dir/results/SBDI/annotation.tsv" "$target"
    echo "Fetched $target ($(wc -l < "$target") lines)"
    if scp -q "${ssh_opts[@]}" "$transfer_host:$remote_dir/results/dada2/ASV_tax.*.tsv" input/ 2>/dev/null; then
      echo "Fetched DADA2 taxonomy table(s): $(cd input && ls ASV_tax.*.tsv | tr '\n' ' ')"
    fi
    ;;

  *)
    usage
    ;;
esac
