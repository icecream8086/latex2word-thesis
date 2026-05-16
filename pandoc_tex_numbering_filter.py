"""Wrapper that runs pandoc-tex-numbering as a Python module (not the bundled .exe).
This ensures modifications to numbering.py take effect."""
import sys
from pandoc_tex_numbering.pandoc_tex_numbering import main
sys.exit(main())
