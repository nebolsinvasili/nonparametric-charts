# Сборка перевода книги
#
# make          — собрать PDF (два прохода) и проверить статус перевода;
# make check    — только проверка (TODO, рисунки, объём);
# make check-strict — то же, но отсутствующие рисунки/битые ссылки = ошибка;
# make clean    — удалить артефакты LaTeX (PDF остаётся);
# make distclean— удалить и PDF.

PY ?= $(if $(wildcard ../.venv/bin/python),$(abspath ../.venv/bin/python),python3)
MAIN = document
SOURCES = $(MAIN).tex chapter-1.tex chapter-2.tex chapter-3.tex chapter-4.tex \
          fig-4.22.tex

#: Диапазон рисунков для `make figures` (подписи FIGURE <глава>.<номер>).
FIGURES ?= 3.8-3.23

.PHONY: all check check-strict figures clean distclean

all: $(MAIN).pdf
	@$(PY) lint_tables.py
	@$(PY) check_translation.py

# pdflatex возвращает 1 при любой ошибке (например, отсутствующий рисунок),
# но PDF при этом собирается. Поэтому ошибки не глушим, а проверяем отдельно:
# make check показывает, что именно не так.
$(MAIN).pdf: $(SOURCES) $(wildcard images/*.png)
	@pdflatex -interaction=nonstopmode $(MAIN).tex >/dev/null || true
	@pdflatex -interaction=nonstopmode $(MAIN).tex >/dev/null || true
	@test -f $(MAIN).pdf || { echo "ОШИБКА: PDF не создан"; exit 1; }
	@echo "собрано: $(MAIN).pdf"

check:
	$(PY) check_translation.py

check-strict:
	$(PY) lint_tables.py
	$(PY) check_translation.py --strict

# Вырезать рисунки из PDF книги по подписям FIGURE <глава>.<номер>.
# Нужен Pillow (есть в .venv). Перезапись: make figures FORCE=--force
figures:
	$(PY) extract_figures.py --figures $(FIGURES) $(FORCE)

clean:
	rm -f *.aux *.log *.out *.toc *.synctex.gz

distclean: clean
	rm -f $(MAIN).pdf
