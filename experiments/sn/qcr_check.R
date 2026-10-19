# Пункт 4.2: проверка средств пакета qcr.
# Задача — выяснить, есть ли в qcr классическая знаковая карта (SN).
# Запуск:
#   R_LIBS=/tmp/opencode/renv/lib/R/library \
#     /tmp/opencode/renv/bin/Rscript experiments/sn/qcr_check.R

suppressMessages(library(qcr))
cat("qcr", as.character(packageVersion("qcr")), "\n")

ns <- ls("package:qcr")
cat("всего функций:", length(ns), "\n")
cat("непараметрические:", paste(sort(grep("^npqcs", ns, value = TRUE)),
                               collapse = ", "), "\n")
cat("со словом sign:", paste(grep("sign", ns, value = TRUE,
                                  ignore.case = TRUE), collapse = ", "), "\n")

# Знаковой карты (SN = n+ - n-) в пакете нет; его непараметрические карты
# многомерны и основаны на глубине данных. Демонстрация npqcs.r:
set.seed(356)
suppressMessages(library(mvtnorm))
G <- rmvnorm(200, mean = c(0, 0), sigma = diag(2))         # опорная выборка
x <- rmvnorm(20, mean = c(1, 1), sigma = 2 * diag(2))       # новые наблюдения
d <- npqcd(x, G)
res <- npqcs.r(d, method = "Liu", alpha = 0.025)
cat("npqcs.r: класс результата —", paste(class(res), collapse = "/"), "\n")
cat("npqcs.r: размерность наблюдений —", ncol(x),
    "(многомерный случай, знаковая карта неприменима)\n")

# Классическая знаковая карта отсутствует; ближайший одномерный аналог —
# атрибутная карта числа несоответствий qcs.np (не знаковая).
cat("есть ли qcs.np (атрибутная np):", "qcs.np" %in% ns, "\n")
