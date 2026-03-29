import argparse
import logging
from pathlib import Path
import pymupdf4llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PDFToMarkdownConverter:
    """
    Utility class to convert PDF files to Markdown.
    Provides a modular class interface for integration with other scripts,
    as well as a CLI interface for manual usage.
    """
    def __init__(self):
        # We can add initialization parameters here in the future if needed
        # (e.g. customized image extraction paths, table processing options)
        pass

    def convert(self, input_pdf: str | Path, output_md: str | Path | None = None) -> str:
        """
        Converts the given PDF file to Markdown format.
        
        Args:
            input_pdf: Path to the input PDF file.
            output_md: Path to save the Markdown output. If None, derives the filename
                       from the input file and saves in the same directory.
            
        Returns:
            The converted markdown string.
        """
        input_path = Path(input_pdf)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        if output_md is None:
            output_md = input_path.with_suffix(".md")
        else:
            output_md = Path(output_md)
            
        logger.info(f"Converting PDF '{input_path}' to Markdown...")
        try:
            # We use pymupdf4llm which natively handles complex formatting, tables, etc., 
            # and returns highly structured MD text.
            md_text = pymupdf4llm.to_markdown(str(input_path))
            
            # Ensure the output directory exists
            output_md.parent.mkdir(parents=True, exist_ok=True)
            output_md.write_text(md_text, encoding="utf-8")
            logger.info(f"Successfully saved Markdown to '{output_md}'")
            
            return md_text
        except Exception as e:
            logger.error(f"Failed to convert PDF: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Convert PDF files to Markdown format.")
    parser.add_argument("input_pdf", type=str, help="Path to the input PDF file")
    parser.add_argument("-o", "--output", type=str, help="Path to the output Markdown file", default=None)
    
    args = parser.parse_args()
    
    converter = PDFToMarkdownConverter()
    try:
        converter.convert(args.input_pdf, args.output)
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
