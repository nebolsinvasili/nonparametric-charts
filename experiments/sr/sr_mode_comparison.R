# sr_mode_comparison.R — контрольные границы SR в реализации автора (npSPC).
#
# Для каждого объёма подгруппы n и каждой настройки far вызывается функция
# shewhart_sr() из пакета npSPC (Nascimento et al., 2026). Функция рисует
# карту и возвращает только строку с ARL, поэтому внутренний графический
# вызов plot_chart() перехватывается: так извлекаются вычисленные пакетом
# границы (ucl) и сама статистика SR.
#
# Пакет имеет два режима: exact = FALSE (по умолчанию) — асимптотические
# границы Limits_asymptotical (дробное z·SD), exact = TRUE — точные границы
# Exact_distribution (квантиль уровня 1 − far/2).
#
# Вход:  experiments/sr/data_sr_modes_<n>.csv (строки = подгруппы,
#        столбцы = наблюдения) — создаётся скриптом sr_modes_experiment.py.
# Выход: experiments/sr/sr_modes_npspc_limits.csv
#
# Запуск (см. 05_modes_experiment.txt):
#   R_LIBS=<renv>/lib/R/library <renv>/bin/Rscript experiments/sr/sr_mode_comparison.R

suppressMessages(library(npSPC))

.cap <- new.env()
assignInNamespace(
  "plot_chart",
  function(statistics, ic, ucl, lcl, name, side, ...) {
    .cap$sr <- statistics
    .cap$ucl <- ucl
    .cap$lcl <- lcl
  },
  ns = "npSPC"
)

far_settings <- c(0.0027, 0.00135)
ns <- c(14L, 16L, 19L)

res <- data.frame()
for (n in ns) {
  X <- as.matrix(read.csv(sprintf("experiments/sr/data_sr_modes_%d.csv", n)))
  Xt <- t(X)                       # строки = наблюдения, столбцы = подгруппы
  for (exact in c(TRUE, FALSE)) {
    for (far in far_settings) {
      arl_str <- shewhart_sr(Xt, mu0 = 0, far = far, side = "two.sided",
                             exact = exact)
      ucl <- .cap$ucl[1]
      res <- rbind(res, data.frame(n = n, far_arg = far,
                                   exact = exact, ucl = ucl,
                                   arl_reported = arl_str))
    }
  }
}

write.csv(res, "experiments/sr/sr_modes_npspc_limits.csv",
          row.names = FALSE)
cat("npSPC SR limits written\n")
print(res)
