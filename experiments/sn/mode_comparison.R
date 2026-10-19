# mode_comparison.R — контрольные границы в реализации автора (пакет npSPC).
#
# Для каждого объёма подгруппы n и каждой настройки far вызывается функция
# shewhart_sn() из пакета npSPC (Nascimento et al., 2026). Функция рисует
# карту и возвращает только строку с ARL, поэтому внутренний графический
# вызов plot_chart() перехватывается: так извлекаются вычисленные пакетом
# границы (ucl) и сама статистика SN.
#
# Вход:  experiments/sn/data_modes_<n>.csv  (строки = подгруппы,
#        столбцы = наблюдения) — создаётся скриптом modes_experiment.py.
# Выход: experiments/sn/modes_npspc_limits.csv
#
# Запуск (см. 05_modes_experiment.txt):
#   R_LIBS=<renv>/lib/R/library <renv>/bin/Rscript experiments/sn/mode_comparison.R

suppressMessages(library(npSPC))

.cap <- new.env()
assignInNamespace(
  "plot_chart",
  function(statistics, ic, ucl, lcl, name, side, ...) {
    .cap$SN <- statistics
    .cap$ucl <- ucl
    .cap$lcl <- lcl
  },
  ns = "npSPC"
)

far_settings <- c(0.0027, 0.00135)
ns <- c(13L, 16L, 19L)

res <- data.frame()
for (n in ns) {
  X <- as.matrix(read.csv(sprintf("experiments/sn/data_modes_%d.csv", n)))
  Xt <- t(X)                       # строки = наблюдения, столбцы = подгруппы
  for (far in far_settings) {
    arl_str <- shewhart_sn(Xt, med = 0, far = far, side = "two.sided")
    a <- .cap$ucl[1]
    q <- (n + a) / 2
    far_att <- 2 * pbinom(q - 1, n, 1 / 2, lower.tail = FALSE)
    res <- rbind(res, data.frame(n = n, far_arg = far, a = a,
                                 far_attained = far_att,
                                 arl_reported = arl_str))
  }
}

write.csv(res, "experiments/sn/modes_npspc_limits.csv", row.names = FALSE)
cat("npSPC limits written\n")
print(res)
