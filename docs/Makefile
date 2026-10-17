# Сборка TeX-документов по теории контрольных границ.
#
#   make        — собрать оба PDF (docs/*.pdf)
#   make sn     — только SN
#   make sr     — только SR
#   make clean  — удалить build/ и собранные PDF (НЕ трогает docs/*.pdf-первоисточники)
#
# Движок: pdflatex (T2A + babel russian → корректная кириллица, стиль CM).
# Вспомогательные файлы (.aux/.log/.out/.toc) складываются в build/.
# Для сборки нужен TeX Live с пакетами pgfplots, booktabs, listings.

LATEX      := pdflatex
BUILDDIR   := build
LATEXFLAGS := -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=$(BUILDDIR)
TARGETS    := sn_bounds_theory.pdf sr_bounds_theory.pdf

.PHONY: all sn sr clean

all: $(TARGETS)

sn: sn_bounds_theory.pdf
sr: sr_bounds_theory.pdf

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

# Двойной проход: оглавление и перекрёстные ссылки.
%.pdf: %.tex | $(BUILDDIR)
	$(LATEX) $(LATEXFLAGS) $< >/dev/null
	$(LATEX) $(LATEXFLAGS) $< >/dev/null
	cp $(BUILDDIR)/$@ $@

# Удаляются только артефакты сборки и собственные PDF;
# исходные PDF в docs/ (книга Чакраборти, Клячкин) не затрагиваются.
clean:
	rm -rf $(BUILDDIR)
	rm -f $(TARGETS)
