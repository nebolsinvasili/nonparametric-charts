#!/usr/bin/env bash
# Подготовка R-окружения для сверок CUSUM с пакетом npSPC.
#
# Идемпотентен: повторный запуск ничего не переустанавливает.
# Окружение по умолчанию — /tmp/opencode/renv (переопределяется RENV=...).
#
# Запуск из корня репозитория:
#   bash experiments/cusum/setup_renv.sh
#
# После установки:
#   R_LIBS=$RENV/lib/R/library RSCRIPT=$RENV/bin/Rscript \
#       poetry run python experiments/cusum/05_cross_validation.py
#
# Требуется: curl, tar, git (права суперпользователя не нужны).

set -euo pipefail

RENV="${RENV:-/tmp/opencode/renv}"
MAMBA_DIR="${MAMBA_DIR:-/tmp/opencode/mm}"
NPSCP_REPO="${NPSCP_REPO:-https://github.com/CER-UFBA/npSPC.git}"
MAMBA="${MAMBA_DIR}/bin/micromamba"
export MAMBA_ROOT_PREFIX="${MAMBA_DIR}/root"
export R_LIBS="${RENV}/lib/R/library"

log() { printf '[setup_renv] %s\n' "$*"; }

if [[ ! -x "${MAMBA}" ]]; then
  log "micromamba не найдена — скачиваю в ${MAMBA_DIR}"
  mkdir -p "${MAMBA_DIR}"
  tmp_dir="$(mktemp -d)"
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest \
    -o "${tmp_dir}/micromamba.tar.bz2"
  tar -xjf "${tmp_dir}/micromamba.tar.bz2" -C "${MAMBA_DIR}" bin/micromamba
  rm -rf "${tmp_dir}"
fi

created=0
if [[ ! -x "${RENV}/bin/Rscript" ]]; then
  log "создаю R-окружение ${RENV} (conda-forge r-base)"
  "${MAMBA}" create -y -p "${RENV}" -c conda-forge r-base
  created=1
fi

if [[ "${created}" -eq 1 ]]; then
  log "ставлю зависимости npSPC (dplyr, purrr)"
  "${MAMBA}" install -y -p "${RENV}" -c conda-forge r-dplyr r-purrr
fi

if ! "${RENV}/bin/Rscript" \
    -e 'quit(status = !requireNamespace("npSPC", quietly = TRUE))' \
    >/dev/null 2>&1; then
  src_dir="${MAMBA_DIR}/npSPC"
  if [[ ! -d "${src_dir}/.git" ]]; then
    log "клонирую npSPC в ${src_dir}"
    git clone --depth 1 "${NPSCP_REPO}" "${src_dir}"
  fi
  log "собираю npSPC"
  "${RENV}/bin/R" CMD INSTALL "${src_dir}" >/dev/null
fi

"${RENV}/bin/Rscript" -e '
suppressMessages(library(npSPC))
cat("R:", R.version.string, "\n")
cat("npSPC:", as.character(packageVersion("npSPC")), "\n")
cat("data1:", paste(dim(data1), collapse = "x"),
    " data2:", paste(dim(data2), collapse = "x"), "\n")
'

log "готово. Экспортируйте:"
log "  RENV=${RENV}"
log "  R_LIBS=${R_LIBS}"
log "  RSCRIPT=${RENV}/bin/Rscript"
