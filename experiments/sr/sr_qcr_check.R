# Пункт 4.2: проверка средств пакета qcr.
# Задача — выяснить, есть ли в qcr классическая знаково-ранговая карта (SR).
# Запуск:
#   R_LIBS=/tmp/opencode/renv/lib/R/library \
#     /tmp/opencode/renv/bin/Rscript experiments/sr/sr_qcr_check.R

suppressMessages(library(qcr))
cat("qcr", as.character(packageVersion("qcr")), "\n")

ns <- ls("package:qcr")
cat("всего функций:", length(ns), "\n")
cat("непараметрические:", paste(sort(grep("^npqcs", ns, value = TRUE)),
                               collapse = ", "), "\n")
cat("со словами rank/ranked:", paste(grep("rank", ns, value = TRUE,
                                          ignore.case = TRUE), collapse = ", "),
    "\n")
cat("со словом wilcox:", paste(grep("wilcox", ns, value = TRUE,
                                    ignore.case = TRUE), collapse = ", "), "\n")

# Знаково-ранговой карты (SR = сумма рангов со знаком) в пакете нет; его
# непараметрические карты многомерны и основаны на глубине данных.
set.seed(356)
suppressMessages(library(mvtnorm))
G <- rmvnorm(200, mean = c(0, 0), sigma = diag(2))         # опорная выборка
x <- rmvnorm(20, mean = c(1, 1), sigma = 2 * diag(2))       # новые наблюдения
d <- npqcd(x, G)
res <- npqcs.r(d, method = "Liu", alpha = 0.025)
cat("npqcs.r: класс результата —", paste(class(res), collapse = "/"), "\n")
cat("npqcs.r: размерность наблюдений —", ncol(x),
    "(многомерный случай, знаково-ранговая карта неприменима)\n")

# Классическая знаково-ранговая карта отсутствует; ближайший одномерный
# аналог — атрибутная карта числа несоответствий qcs.np (не знаково-ранговая).
cat("есть ли qcs.np (атрибутная np):", "qcs.np" %in% ns, "\n")
