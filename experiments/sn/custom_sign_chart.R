# Пункт 4.3: SN-карта "с нуля" средствами базового R.
# Два подхода: знаковый с нормальной аппроксимацией границ и знаковый точный.
# Показывает, как самодельные реализации ошибаются на границах.

sn_chart_custom <- function(X, med = 0, far = 0.0027, method = "normal") {
  n <- nrow(X)                      # наблюдений в подгруппе
  SN <- colSums(sign(X - med))      # знаковая статистика подгрупп
  if (method == "normal") {
    # SN = 2T - n, Var(SN) = n  =>  границы +-z*sqrt(n)
    a <- ceiling(qnorm(1 - far / 2) * sqrt(n))
  } else {
    a <- NA
    for (k in seq(if (n %% 2) 1 else 2, n, by = 2)) {
      if (pbinom((n + k) / 2 - 1, n, 1/2, lower.tail = FALSE) <= far / 2) {
        a <- k
        break
      }
    }
    if (is.na(a)) a <- n
  }
  list(SN = SN, a = a, signal = which(abs(SN) >= a))
}

# Точное правило (эталон).
sn_exact <- function(n, far = 0.0027) {
  for (k in seq(if (n %% 2) 1 else 2, n, by = 2)) {
    if (pbinom((n + k) / 2 - 1, n, 1/2, lower.tail = FALSE) <= far / 2)
      return(k)
  }
  n
}

cat(sprintf("%3s %8s %8s %6s %11s\n", "n", "exact", "normal", "diff", "FAR(normal)"))
for (n in c(10, 16, 20, 25, 30, 40, 50, 100)) {
  ex <- sn_exact(n)
  z <- qnorm(1 - 0.0027 / 2)
  ap <- ceiling(z * sqrt(n))
  # достигнутый FAR при нормальной границе (если она достижима по чётности)
  if ((ap - n) %% 2 == 0 && ap <= n) {
    far_ap <- 2 * pbinom((n + ap) / 2 - 1, n, 1/2, lower.tail = FALSE)
    far_s <- sprintf("%.5f", far_ap)
  } else {
    far_s <- "n/d"
  }
  cat(sprintf("%3d %8d %8d %6d %11s\n", n, ex, ap, ap - ex, far_s))
}

# Демонстрация на данных: FAR при нормальной и точной границах (n = 16, IC).
set.seed(7)
n <- 16; m <- 20000
X <- matrix(rnorm(n * m), nrow = n, ncol = m)
c1 <- sn_chart_custom(X, med = 0, method = "normal")
c2 <- sn_chart_custom(X, med = 0, method = "exact")
cat(sprintf("\nn=16, IC: normal a=%d, FA=%d, FAR=%.5f\n",
            c1$a, length(c1$signal), length(c1$signal) / m))
cat(sprintf("n=16, IC: exact  a=%d, FA=%d, FAR=%.5f\n",
            c2$a, length(c2$signal), length(c2$signal) / m))
