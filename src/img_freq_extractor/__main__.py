"""`python -m img_freq_extractor` を可能にするエントリー。"""
from .cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
