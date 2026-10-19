# Пункт 4.3: SR-карта "с нуля" средствами базового R.
# Два подхода: знаково-ранговая с нормальной аппроксимацией границ и
# знаково-ранговая точная (перебор 2^n). Показывает, как самодельные
# реализации ошибаются на границах.

# Точное распределение SR через ДП-свёртку значений +-j.
sr_dist <- function(n) {
  dp <- c(`0` = 1)
  for (j in 1:n) {
    idx <- as.integer(names(dp))
    nxt <- dp * 0
    for (k in seq_along(dp)) {
      for (v in c(idx[k] + j, idx[k] - j)) {
        key <- as.character(v)
        nxt[key] <- (if (is.na(nxt[key])) 0 else nxt[key]) + dp[k]
      }
    }
    dp <- nxt[!is.na(nxt) & nxt > 0]
  }
  dp / 2^n
}

# Точное правило (консервативное).
sr_exact <- function(n, far = 0.0027) {
  S <- n * (n + 1) / 2
  d <- sr_dist(n)
  vals <- as.integer(names(d))
  for (a in seq(if (S %% 2) 1 else 2, S, by = 2)) {
    if (sum(d[vals >= a]) <= far / 2) return(a)
  }
  S
}

sr_chart_custom <- function(X, med = 0, far = 0.0027, method = "normal") {
  n <- nrow(X)                                   # наблюдений в подгруппе
  S <- n * (n + 1) / 2
  R <- apply(abs(X - med), 2, rank)              # ранги |X| в подгруппе
  Tplus <- colSums((X - med > 0) * R)
  SR <- 2 * Tplus - S                            # знаково-ранговая статистика
  if (method == "normal") {
    # Var(SR) = n(n+1)(2n+1)/6  =>  границы +-z*SD(SR)
    a <- ceiling(qnorm(1 - far / 2) * sqrt(n * (n + 1) * (2 * n + 1) / 6))
  } else {
    a <- sr_exact(n, far)
  }
  list(SR = SR, a = a, signal = which(abs(SR) >= a))
}

cat(sprintf("%3s %8s %8s %6s %11s\n", "n", "exact", "normal", "diff", "FAR(normal)"))
for (n in c(10, 16, 20, 25, 30, 40)) {
  ex <- sr_exact(n)
  ap <- ceiling(qnorm(1 - 0.0027 / 2) * sqrt(n * (n + 1) * (2 * n + 1) / 6))
  d <- sr_dist(n); vals <- as.integer(names(d))
  far_ap <- 2 * sum(d[vals >= min(ap, n * (n + 1) / 2)])
  cat(sprintf("%3d %8d %8d %6d %11.5f\n", n, ex, ap, ap - ex, far_ap))
}

# Демонстрация на данных: FAR при нормальной и точной границах (n = 16, IC).
set.seed(7)
n <- 16; m <- 20000
X <- matrix(rnorm(n * m), nrow = n, ncol = m)
c1 <- sr_chart_custom(X, med = 0, method = "normal")
c2 <- sr_chart_custom(X, med = 0, method = "exact")
cat(sprintf("\nn=16, IC: normal a=%d, FA=%d, FAR=%.5f\n",
            c1$a, length(c1$signal), length(c1$signal) / m))
cat(sprintf("n=16, IC: exact  a=%d, FA=%d, FAR=%.5f\n",
            c2$a, length(c2$signal), length(c2$signal) / m))
