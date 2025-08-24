# Makefile for Kindle Clippings Parser

# Default target
.PHONY: all markdown json clean help

# Directories
INPUT_DIR = input
OUTPUT_DIR = output
INPUT_FILE = "$(INPUT_DIR)/My Clippings.txt"

# Output files
MARKDOWN_OUTPUT = $(OUTPUT_DIR)/clippings.md
JSON_OUTPUT = $(OUTPUT_DIR)/clippings.json

# Default target - generates both markdown and JSON
all: markdown json

# Generate markdown output
markdown:
	@echo "Generating markdown output..."
	@mkdir -p $(OUTPUT_DIR)
	uv run python parser.py $(INPUT_FILE) -o "$(MARKDOWN_OUTPUT)"
	@echo "Markdown output generated at $(MARKDOWN_OUTPUT)"

# Generate JSON output
json:
	@echo "Generating JSON output..."
	@mkdir -p $(OUTPUT_DIR)
	uv run python parser.py $(INPUT_FILE) -o "$(MARKDOWN_OUTPUT)" -j
	@echo "JSON output generated at $(JSON_OUTPUT)"

# Clean generated files
clean:
	@echo "Cleaning output files..."
	@rm -f $(MARKDOWN_OUTPUT) $(JSON_OUTPUT)
	@echo "Output files cleaned"

# Help target
help:
	@echo "Available targets:"
	@echo "  all      - Generate both markdown and JSON output"
	@echo "  markdown - Generate markdown output only"
	@echo "  json     - Generate JSON output only"
	@echo "  clean    - Remove generated output files"
	@echo "  help     - Show this help message"