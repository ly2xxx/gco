import argparse
import logging
from pathlib import Path
from markitdown import MarkItDown

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class DocToMarkdownConverter:
    """
    Utility class to convert DOCX and other Document files to Markdown.
    Provides a modular class interface for integration with other scripts,
    as well as a CLI interface for manual usage.
    """
    def __init__(self):
        # Initialize markitdown client
        self.md_client = MarkItDown()

    def convert(self, input_doc: str | Path, output_md: str | Path | None = None) -> str:
        """
        Converts the given Document file to Markdown format.
        
        Args:
            input_doc: Path to the input Document file (e.g., .docx).
            output_md: Path to save the Markdown output. If None, derives the filename
                       from the input file and saves in the same directory.
            
        Returns:
            The converted markdown string.
        """
        input_path = Path(input_doc)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        if output_md is None:
            output_md = input_path.with_suffix(".md")
        else:
            output_md = Path(output_md)
            
        logger.info(f"Converting Document '{input_path}' to Markdown...")
        try:
            # markitdown converts DOCX (and other common formats) into clean Markdown
            result = self.md_client.convert(str(input_path))
            md_text = result.text_content
            
            # Ensure the output directory exists
            output_md.parent.mkdir(parents=True, exist_ok=True)
            output_md.write_text(md_text, encoding="utf-8")
            logger.info(f"Successfully saved Markdown to '{output_md}'")
            
            return md_text
        except Exception as e:
            logger.error(f"Failed to convert Document: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Convert Document files (like DOCX) to Markdown format.")
    parser.add_argument("input_doc", type=str, help="Path to the input Document file")
    parser.add_argument("-o", "--output", type=str, help="Path to the output Markdown file", default=None)
    
    args = parser.parse_args()
    
    converter = DocToMarkdownConverter()
    try:
        converter.convert(args.input_doc, args.output)
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
