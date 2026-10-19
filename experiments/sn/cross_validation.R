# Перекрёстная проверка SN-карты: пакет npSPC против нашей реализации.
# Готовит одинаковые данные для R и Python, считает пределы и сигналы.
# Запуск:
#   R_LIBS=/tmp/opencode/renv/lib/R/library \
#     /tmp/opencode/renv/bin/Rscript experiments/sn/cross_validation.R

suppressMessages(library(npSPC))

n <- 16          # размер подгруппы
m <- 3000        # число подгрупп
shift_at <- 2001 # с этой подгруппы вводится сдвиг медианы на 1 сигму

set.seed(20261018)

# Столбец = подгруппа, строка = наблюдение внутри подгруппы (формат npSPC).
X <- matrix(rnorm(n * m), nrow = n, ncol = m)
X[, shift_at:m] <- X[, shift_at:m] + 1.0
rownames(X) <- paste0("obs", 1:n)

# Сохраняем данные для Python (та же матрица).
write.csv(X, "experiments/sn/data_cross.csv", row.names = FALSE)

# --- Правило границ npSPC (R/shewhart_sn.R) ---
npspc_limits <- function(n, far = 0.0027) {
  tail <- pbinom(0:n, n, 1/2, lower.tail = FALSE)
  q <- max(which(tail >= far), na.rm = TRUE)
  q <- min(n, q + 1, na.rm = TRUE)
  list(a = 2 * q - n, far = 2 * tail[q])
}

# --- Книжное правило (наша реализация) ---
book_limits <- function(n, far0 = 0.0027) {
  for (a in seq(if (n %% 2) 1 else 2, n, by = 2)) {
    if (pbinom((n + a) / 2 - 1, n, 1/2, lower.tail = FALSE) <= far0 / 2)
      return(list(a = a, far = 2 * pbinom((n + a) / 2 - 1, n, 1/2,
                                         lower.tail = FALSE)))
  }
  list(a = n, far = 2 * pbinom(0, n, 1/2, lower.tail = FALSE))
}

np <- npspc_limits(n)
bk <- book_limits(n)
cat(sprintf("npSPC: a=%d FAR=%.6f ARL0=%.1f\n", np$a, np$far, 1 / np$far))
cat(sprintf("книга: a=%d FAR=%.6f ARL0=%.1f\n", bk$a, bk$far, 1 / bk$far))

# --- Статистика SN по столбцам (как в shewhart_sn) ---
SN <- colSums(X > 0) - colSums(X < 0)

sig_np <- which(abs(SN) >= np$a)
sig_bk <- which(abs(SN) >= bk$a)

cat(sprintf("подгрупп: %d; сдвиг с %d\n", m, shift_at))
cat(sprintf("сигналов npSPC (|SN|>=%d): %d; из них до сдвига: %d\n",
            np$a, length(sig_np), sum(sig_np < shift_at)))
cat(sprintf("сигналов книга (|SN|>=%d): %d; из них до сдвига: %d\n",
            bk$a, length(sig_bk), sum(sig_bk < shift_at)))

# --- Ручной расчёт пределов (для протокола) ---
cat("первые 12 значений SN:", paste(head(SN, 12), collapse = " "), "\n")

# --- Выгрузка для сравнения с Python ---
out <- data.frame(idx = 1:m, SN = SN,
                  sig_np = abs(SN) >= np$a, sig_bk = abs(SN) >= bk$a)
write.csv(out, "experiments/sn/data_cross_out.csv", row.names = FALSE)
cat("файлы записаны\n")
