# Кросс-валидация CUSUM-SN/SR: эталонный пакет npSPC (R) — сторона R.
#
# Готовит общие данные и выгружает в experiments/cusum/xval/:
#   * config.csv      — сетка (dataset, statistic, k, h);
#   * data.csv        — фиксированные наборы данных (long-формат);
#   * steps.csv       — статистики подгрупп Sn/Sr (эталон npSPC + вариант n_eff);
#   * stats.csv       — кумулятивные суммы S+ / S- (перехват из plot_chart);
#   * signals.csv     — индекс первой тревоги по сторонам;
#   * arl_config.csv  — конфигурации имитационного ARL;
#   * arl_<name>.csv  — данные имитаций (sim × group × наблюдения);
#   * arl_rl.csv      — длина серии по каждому прогону (сторона — в sided).
#
# Источник метода: Chakraborti & Graham (2019), §4.2.2.1 (стр. 202–203),
# §4.2.2.4 (стр. 205–206); данные data1 — табл. 4.7a (стр. 226),
# data2 — табл. 4.6 (стр. 22).
# Эталон: npSPC (CER-UFBA/npSPC, функциями cusum_sn / cusum_sr).
#
# Запуск из корня репозитория:
#   R_LIBS=/tmp/opencode/renv/lib/R/library \
#     /tmp/opencode/renv/bin/Rscript experiments/cusum/05_cross_validation.R

suppressMessages(library(npSPC))

OUT <- "experiments/cusum/xval"
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)

# --- перехват кумулятивных сумм, которые npSPC передаёт в plot_chart ---
.cap <- new.env()
.cap$plus <- NULL
.cap$minus <- NULL
.cap$side <- NULL

orig_plot_chart <- getFromNamespace("plot_chart", "npSPC")
assignInNamespace(
  "plot_chart",
  function(ic, statistics, statistics2 = NULL, ucl, lcl, name = NULL,
           side) {
    .cap$plus <- statistics
    .cap$minus <- statistics2
    .cap$side <- side
    invisible(NULL)
  },
  ns = "npSPC"
)

capture_stats <- function(expr) {
  .cap$plus <- NULL
  .cap$minus <- NULL
  force(expr)
  list(plus = .cap$plus, minus = .cap$minus)
}

# --- статистика подгруппы (эталон npSPC: Sn и Sr = 2 T+ - n(n+1)/2) ---
sn_step <- function(X, med = 0) {
  colSums(X > med) - colSums(X < med)
}

sr_step <- function(X, med = 0) {
  n <- nrow(X)
  m <- ncol(X)
  v_plus <- vapply(
    seq_len(m),
    function(i) as.numeric(wilcox.test(X[, i], mu = med)$statistic),
    numeric(1)
  )
  # формула npSPC: центрирование по полному n (некорректно при нулях)
  npspc <- 2 * v_plus - n * (n + 1) / 2
  # корректное центрирование по числу ненулевых отклонений
  n_eff <- vapply(
    seq_len(m),
    function(i) sum(X[, i] != med),
    numeric(1)
  )
  neff <- 2 * v_plus - n_eff * (n_eff + 1) / 2
  list(npspc = npspc, neff = neff)
}

# --- сетки параметров (единый источник истины; Python читает config.csv) ---
k_grid <- function(statistic, n) {
  if (statistic == "SN") {
    return(c(1, 2, 3, 4, 6, 8)[c(1, 2, 3, 4, 6, 8) <= n])
  }
  S <- n * (n + 1) / 2
  round(S * c(0.1, 0.25, 0.5), 2)
}

h_grid <- function(statistic, n) {
  if (statistic == "SN") {
    return(c(2, 3, 4, 5, 6, 8, 10, 12, 16))
  }
  S <- n * (n + 1) / 2
  ceiling(S * c(0.2, 0.35, 0.5, 0.75, 1.0))
}

# --- наборы данных (формат npSPC: строка — наблюдение, столбец — подгруппа) ---
set.seed(20261020)

n_norm <- 10
m_norm <- 25
X_norm <- matrix(rnorm(n_norm * m_norm), nrow = n_norm)
X_shift <- X_norm
X_shift[, 16:m_norm] <- X_shift[, 16:m_norm] + 0.5

n_ties <- 8
m_ties <- 20
X_ties <- matrix(round(rnorm(n_ties * m_ties), 1), nrow = n_ties)

n_zero <- 6
m_zero <- 20
X_zero <- matrix(round(rnorm(n_zero * m_zero), 1), nrow = n_zero)
# ровно один точный ноль в каждой подгруппе первой половины набора
X_zero[cbind(c(2, 4, 6, 1, 3, 5), 1:6)] <- 0

datasets <- lapply(
  list(
    data1   = data1,
    data2   = data2,
    norm10  = X_norm,
    shift10 = X_shift,
    ties8   = X_ties,
    zeros6  = X_zero
  ),
  as.matrix
)

# какой статистикой проверяем набор
spec <- list(
  data1   = c("SR"),
  data2   = c("SN", "SR"),
  norm10  = c("SN", "SR"),
  shift10 = c("SN", "SR"),
  ties8   = c("SN", "SR"),
  zeros6  = c("SN", "SR")
)

# --- 1. Данные (long-формат) ---
data_rows <- do.call(rbind, lapply(names(datasets), function(nm) {
  X <- datasets[[nm]]
  data.frame(
    dataset = nm,
    group = rep(seq_len(ncol(X)), each = nrow(X)),
    obs = rep(seq_len(nrow(X)), times = ncol(X)),
    value = as.vector(X)
  )
}))
write.csv(data_rows, file.path(OUT, "data.csv"), row.names = FALSE)

# --- 2. Статистики подгрупп ---
steps_rows <- do.call(rbind, lapply(names(datasets), function(nm) {
  X <- datasets[[nm]]
  out <- list()
  if ("SN" %in% spec[[nm]]) {
    out[["SN"]] <- data.frame(step = sn_step(X), step_alt = NA_real_)
  }
  if ("SR" %in% spec[[nm]]) {
    sr <- sr_step(X)
    out[["SR"]] <- data.frame(step = sr$npspc, step_alt = sr$neff)
  }
  do.call(rbind, lapply(names(out), function(stat) {
    data.frame(
      dataset = nm,
      statistic = stat,
      group = seq_len(ncol(X)),
      step = out[[stat]]$step,
      step_alt = out[[stat]]$step_alt
    )
  }))
}))
write.csv(steps_rows, file.path(OUT, "steps.csv"), row.names = FALSE)

# --- 3. Конфигурации (dataset × statistic × k × h) ---
config_rows <- do.call(rbind, lapply(names(datasets), function(nm) {
  X <- datasets[[nm]]
  n <- nrow(X)
  do.call(rbind, lapply(spec[[nm]], function(stat) {
    grid <- expand.grid(
      k = k_grid(stat, n),
      h = h_grid(stat, n)
    )
    data.frame(
      dataset = nm,
      statistic = stat,
      n = n,
      k = grid$k,
      h = grid$h
    )
  }))
}))
write.csv(config_rows, file.path(OUT, "config.csv"), row.names = FALSE)

# --- 4. Кумулятивные суммы S+/S- и сигналы ---
#
# npSPC хранит суммы в векторе длины m, где элемент 1 — фиктивный нуль,
# а элементы 2..m — суммы после подгрупп 2..m (первая подгруппа теряется),
# поэтому дополнительно считается «исправленная» рекурсия по шагам.
cumsum_seq <- function(step, k) {
  m <- length(step)
  plus <- minus <- numeric(m)
  plus[1] <- max(0, step[1] - k)
  minus[1] <- min(0, step[1] + k)
  if (m > 1) {
    for (t in 2:m) {
      plus[t] <- max(0, plus[t - 1] + step[t] - k)
      minus[t] <- min(0, minus[t - 1] + step[t] + k)
    }
  }
  list(plus = plus, minus = minus)
}

signal_of <- function(seq, h, side) {
  hits <- switch(
    side,
    upper = which(seq$plus >= h),
    lower = which(seq$minus <= -h),
    two.sided = sort(c(which(seq$plus >= h), which(seq$minus <= -h)))
  )
  if (length(hits) == 0) NA_integer_ else as.integer(hits[1])
}

dataset_steps <- lapply(datasets, function(X) {
  sr <- sr_step(X)
  list(SN = sn_step(X), SR = sr$npspc)
})

stats_rows <- list()
signal_rows <- list()
run <- function(statistic, X, med, k, h, side, plot) {
  if (statistic == "SN") {
    cusum_sn(X, med = med, k = k, h = h, plot = plot, side = side)
  } else {
    cusum_sr(X, med = med, k = k, h = h, plot = plot, side = side)
  }
}

for (i in seq_len(nrow(config_rows))) {
  cfg <- config_rows[i, ]
  X <- datasets[[cfg$dataset]]
  snap <- capture_stats(run(cfg$statistic, X, 0, cfg$k, cfg$h,
                            "two.sided", plot = TRUE))
  m <- ncol(X)
  group <- seq_len(m)
  stats_rows[[length(stats_rows) + 1]] <- data.frame(
    dataset = cfg$dataset,
    statistic = cfg$statistic,
    k = cfg$k,
    group = group,
    plus = c(NA_real_, snap$plus[-1]),
    minus = c(NA_real_, snap$minus[-1])
  )
  seq <- cumsum_seq(dataset_steps[[cfg$dataset]][[cfg$statistic]], cfg$k)
  for (side in c("upper", "lower", "two.sided")) {
    idx <- suppressWarnings(
      run(cfg$statistic, X, 0, cfg$k, cfg$h, side, plot = FALSE)
    )
    signal_rows[[length(signal_rows) + 1]] <- data.frame(
      dataset = cfg$dataset,
      statistic = cfg$statistic,
      k = cfg$k,
      h = cfg$h,
      side = side,
      signal_npspc = if (length(idx) == 0 || is.na(idx)) NA_integer_
                     else as.integer(idx),
      signal_fixed = signal_of(seq, cfg$h, side)
    )
  }
}
write.csv(do.call(rbind, stats_rows), file.path(OUT, "stats.csv"),
          row.names = FALSE)
write.csv(do.call(rbind, signal_rows), file.path(OUT, "signals.csv"),
          row.names = FALSE)

# --- 5. Имитационный ARL на общих данных ---
arl_config <- data.frame(
  name = c("sn_ic", "sn_shift", "sn_two", "sr_ic", "sr_shift"),
  statistic = c("SN", "SN", "SN", "SR", "SR"),
  n = c(10, 10, 10, 4, 4),
  k = c(1, 1, 1, 2, 2),
  h = c(4, 4, 4, 6, 6),
  shift = c(0, 0.5, 0, 0, 0.5),
  sided = c("upper", "upper", "two.sided", "upper", "upper"),
  n_sim = c(150, 150, 150, 100, 100),
  t = c(300, 300, 300, 250, 250)
)
write.csv(arl_config, file.path(OUT, "arl_config.csv"), row.names = FALSE)

set.seed(20261021)
rl_rows <- list()
for (i in seq_len(nrow(arl_config))) {
  cfg <- arl_config[i, ]
  blocks <- list()
  rl_npspc <- rl_fixed <- rep(NA_real_, cfg$n_sim)
  for (s in seq_len(cfg$n_sim)) {
    X <- matrix(rnorm(cfg$n * cfg$t), nrow = cfg$n)
    if (cfg$shift != 0) X <- X + cfg$shift
    idx <- suppressWarnings(
      run(cfg$statistic, X, 0, cfg$k, cfg$h, cfg$sided, plot = FALSE)
    )
    rl_npspc[s] <- if (length(idx) == 0 || is.na(idx)) NA_real_
                  else as.integer(idx)
    step <- if (cfg$statistic == "SN") sn_step(X) else sr_step(X)$npspc
    rl_fixed[s] <- signal_of(cumsum_seq(step, cfg$k), cfg$h, cfg$sided)
    blocks[[s]] <- data.frame(
      sim = s,
      group = rep(seq_len(cfg$t), each = cfg$n),
      obs = rep(seq_len(cfg$n), times = cfg$t),
      value = as.vector(X)
    )
  }
  write.csv(do.call(rbind, blocks),
            file.path(OUT, paste0("arl_", cfg$name, ".csv")), row.names = FALSE)
  rl_rows[[length(rl_rows) + 1]] <- data.frame(
    config = cfg$name,
    sided = cfg$sided,
    sim = seq_len(cfg$n_sim),
    rl = rl_fixed,
    rl_npspc = rl_npspc
  )
  cat(sprintf("ARL R: %-9s %s, n=%d, k=%g, h=%g, shift=%g -> ARL=%.2f (%d/%d без тревоги)\n",
              cfg$name, cfg$statistic, cfg$n, cfg$k, cfg$h, cfg$shift,
              mean(rl_fixed, na.rm = TRUE), sum(is.na(rl_fixed)), cfg$n_sim))
}
write.csv(do.call(rbind, rl_rows), file.path(OUT, "arl_rl.csv"),
          row.names = FALSE)

cat(sprintf("Выгружено в %s\n", OUT))
