# Перекрёстная проверка SR-карты: пакет npSPC против нашей реализации.
# Готовит одинаковые данные для R и Python, считает пределы и сигналы.
# Запуск:
#   R_LIBS=/tmp/opencode/renv/lib/R/library \
#     /tmp/opencode/renv/bin/Rscript experiments/sr/sr_cross_validation.R

suppressMessages(library(npSPC))

n <- 16          # размер подгруппы
m <- 3000        # число подгрупп
shift_at <- 2001 # с этой подгруппы вводится сдвиг медианы на 1 сигму

set.seed(20261018)

# Столбец = подгруппа, строка = наблюдение внутри подгруппы (формат npSPC).
X <- matrix(rnorm(n * m), nrow = n, ncol = m)
X[, shift_at:m] <- X[, shift_at:m] + 1.0
rownames(X) <- paste0("obs", 1:n)

write.csv(X, "experiments/sr/data_sr_cross.csv", row.names = FALSE)

# --- Точное распределение SR (перебор 2^n знаковых наборов) ---
sr_dist <- function(n) {
  M <- as.matrix(expand.grid(rep(list(c(-1, 1)), n)))
  s <- as.vector(M %*% (1:n))
  table(s) / 2^n
}

# --- Книжное правило (консервативное): наименьшее достижимое a ---
book_limits <- function(n, far0 = 0.0027) {
  S <- n * (n + 1) / 2
  d <- sr_dist(n)
  vals <- as.integer(names(d))
  start <- if (S %% 2) 1 else 2
  for (a in seq(start, S, by = 2)) {
    p <- sum(d[vals >= a])
    if (p <= far0 / 2)
      return(list(a = a, far = 2 * p))
  }
  list(a = S, far = 2 * sum(d[vals >= S]))
}

# --- Пределы npSPC exact=TRUE (Exact_distribution, alpha = far/2) ---
.cap <- new.env()
assignInNamespace(
  "plot_chart",
  function(statistics, ic, ucl, lcl, name, side, ...) {
    .cap$sr <- statistics; .cap$ucl <- ucl; .cap$lcl <- lcl
  },
  ns = "npSPC"
)
invisible(shewhart_sr(X, mu0 = 0, far = 0.0027, side = "two.sided",
                      exact = TRUE))
a_np <- .cap$ucl[1]
SR <- .cap$sr

bk <- book_limits(n)
cat(sprintf("npSPC exact: a=%d\n", a_np))
cat(sprintf("книга: a=%d FAR=%.6f ARL0=%.1f\n", bk$a, bk$far, 1 / bk$far))

sig_np <- which(abs(SR) >= a_np)
sig_bk <- which(abs(SR) >= bk$a)

cat(sprintf("подгрупп: %d; сдвиг с %d\n", m, shift_at))
cat(sprintf("сигналов npSPC (|SR|>=%d): %d; из них до сдвига: %d\n",
            a_np, length(sig_np), sum(sig_np < shift_at)))
cat(sprintf("сигналов книга (|SR|>=%d): %d; из них до сдвига: %d\n",
            bk$a, length(sig_bk), sum(sig_bk < shift_at)))

cat("первые 12 значений SR:", paste(head(SR, 12), collapse = " "), "\n")

out <- data.frame(idx = 1:m, SR = SR,
                  sig_np = abs(SR) >= a_np, sig_bk = abs(SR) >= bk$a)
write.csv(out, "experiments/sr/data_sr_cross_out.csv", row.names = FALSE)
cat("файлы записаны\n")
