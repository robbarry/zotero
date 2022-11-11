import os
from dotenv import load_dotenv

HOME = os.path.expanduser("~")
load_dotenv(os.path.join(HOME, ".config", "zotero-aleph", ".env"))
