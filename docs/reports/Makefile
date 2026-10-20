# Сборка TeX-отчётов: верификация знаковой (SN), знаково-ранговой (SR)
# карт Шухарта и непараметрических CUSUM (SN/SR).
#
#   make        — собрать все PDF (docs/reports/*.pdf)
#   make snver  — только верификацию SN
#   make srver  — только верификацию SR
#   make cusum  — только верификацию CUSUM
#   make check  — проверить логи (ошибки, undefined, overfull/underfull)
#   make clean  — удалить build/ и собранные PDF (НЕ трогает PDF-первоисточники в docs/ref/)
#
# Запуск из этого каталога: cd docs/reports && make
# Движок: pdflatex (T2A + babel russian → корректная кириллица, стиль CM).
# Вспомогательные файлы (.aux/.log/.out/.toc) складываются в build/.
# Для сборки нужен TeX Live с пакетами pgfplots, booktabs, listings.

LATEX      := pdflatex
BUILDDIR   := build
LATEXFLAGS := -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=$(BUILDDIR)
TARGETS    := sn_verification.pdf sr_verification.pdf cusum_verification.pdf

.PHONY: all snver srver cusum check clean

all: $(TARGETS)

snver: sn_verification.pdf
srver: sr_verification.pdf
cusum: cusum_verification.pdf

# Макросы графиков отчёта SR генерируются скриптом (не редактировать вручную).
sr_macros.tex:
	cd ../.. && poetry run python experiments/sr/sr_gen_figdata.py > docs/reports/sr_macros.tex

sr_verification.pdf: sr_macros.tex

# Макросы графиков отчёта CUSUM генерируются скриптом (не редактировать вручную).
cusum_macros.tex:
	cd ../.. && poetry run python experiments/cusum/06_gen_figdata.py > docs/reports/cusum_macros.tex

cusum_verification.pdf: cusum_macros.tex

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

# Двойной проход: оглавление и перекрёстные ссылки.
%.pdf: %.tex | $(BUILDDIR)
	$(LATEX) $(LATEXFLAGS) $< >/dev/null
	$(LATEX) $(LATEXFLAGS) $< >/dev/null
	cp $(BUILDDIR)/$@ $@

# Проверка логов: ошибки/undefined — ненулевой код возврата,
# overfull/underfull — только информационно (норма проекта: < 8 pt).
check: $(TARGETS)
	@status=0; \
	for log in $(BUILDDIR)/*.log; do \
	  name=$$(basename $$log .log); \
	  over=$$(grep -c "Overfull \\\\hbox" $$log || true); \
	  under=$$(grep -c "Underfull \\\\hbox" $$log || true); \
	  bad=$$(grep -cE "Undefined control sequence|LaTeX Error|undefined references|Citation .* undefined" $$log || true); \
	  printf "%-26s overfull=%-3s underfull=%-3s errors=%s\n" \
	    "$$name" "$$over" "$$under" "$$bad"; \
	  if [ "$$bad" -ne 0 ]; then status=1; fi; \
	done; \
	exit $$status

# Удаляются только артефакты сборки и собственные PDF;
# PDF-первоисточники в docs/ref/ (книга Чакраборти, Клячкин) не затрагиваются.
clean:
	rm -rf $(BUILDDIR)
	rm -f $(TARGETS)
