# Сборка TeX-отчётов: верификация знаковой карты (SN) и знаково-ранговой (SR).
#
#   make        — собрать все PDF (docs/reports/*.pdf)
#   make snver  — только верификацию SN
#   make srver  — только верификацию SR
#   make clean  — удалить build/ и собранные PDF (НЕ трогает PDF-первоисточники в docs/ref/)
#
# Запуск из этого каталога: cd docs/reports && make
# Движок: pdflatex (T2A + babel russian → корректная кириллица, стиль CM).
# Вспомогательные файлы (.aux/.log/.out/.toc) складываются в build/.
# Для сборки нужен TeX Live с пакетами pgfplots, booktabs, listings.

LATEX      := pdflatex
BUILDDIR   := build
LATEXFLAGS := -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=$(BUILDDIR)
TARGETS    := sn_verification.pdf sr_verification.pdf

.PHONY: all snver srver clean

all: $(TARGETS)

snver: sn_verification.pdf
srver: sr_verification.pdf

# Макросы графиков отчёта SR генерируются скриптом (не редактировать вручную).
sr_macros.tex:
	cd ../.. && poetry run python experiments/sr/sr_gen_figdata.py > docs/reports/sr_macros.tex

sr_verification.pdf: sr_macros.tex

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

# Двойной проход: оглавление и перекрёстные ссылки.
%.pdf: %.tex | $(BUILDDIR)
	$(LATEX) $(LATEXFLAGS) $< >/dev/null
	$(LATEX) $(LATEXFLAGS) $< >/dev/null
	cp $(BUILDDIR)/$@ $@

# Удаляются только артефакты сборки и собственные PDF;
# PDF-первоисточники в docs/ref/ (книга Чакраборти, Клячкин) не затрагиваются.
clean:
	rm -rf $(BUILDDIR)
	rm -f $(TARGETS)
