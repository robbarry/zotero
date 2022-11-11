import os
import time
import logging
import argparse
import dataset
from pyzotero import zotero
from yaml import safe_load


ZOTERO_STORAGE_PATH = os.getenv("ZOTERO_STORAGE_PATH")
ZOTERO_DBPATH = os.getenv("ZOTERO_DBPATH")
ZOTERO_DBFILE = os.path.join(ZOTERO_DBPATH, "data.db")
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_USER_ID = os.getenv("ZOTERO_USER_ID")
ZOTERO_TMP_PATH = os.getenv("ZOTERO_TMP_PATH")

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# set the log function to log
log = logging


def get_zotero_libraries():
    library_file = os.path.join(ZOTERO_DBPATH, "libraries.yml")
    libs = safe_load(open(library_file).read())
    for key, values in libs.items():
        libs[key]["save_root"] = os.path.join(ZOTERO_STORAGE_PATH, values["name"])
        libs[key]["save_path"] = os.path.join(libs[key]["save_root"], "Zotero")
    return libs


def fetch_from_zotero():
    imported = False
    zot = zotero.Zotero(ZOTERO_USER_ID, "user", ZOTERO_API_KEY)
    db = dataset.connect("sqlite:///{}".format(ZOTERO_DBFILE))

    libraries = get_zotero_libraries()

    items = zot.top(limit=10)

    # we've retrieved the latest five top-level items in our library
    # we can print each item's item type and ID
    for item in items:
        title = item["data"].get("title")
        type = item["data"].get("itemType")
        key = item["data"].get("key")
        collections = item["data"].get("collections", [])

        paths = []
        for collection in collections:
            if collection in libraries:
                save_path = libraries[collection]["save_path"]
                paths.append(save_path)
                os.makedirs(save_path, exist_ok=True)

        if paths:
            for child in zot.children(key):
                subkey = child["data"].get("key")

                # get the child item's metadata
                row = {
                    "stamp": time.time(),
                    "key": subkey,
                    "title": title + " " + child["data"].get("title"),
                    "type": child["data"].get("itemType"),
                }

                # check if the child item is already in the database
                if db["items"].find_one(key=subkey):
                    continue

                if child["data"]["title"] == "Link":
                    continue

                db["items"].insert(row)

                name = row["title"]

                # get a file-safe version of name
                filename = name.replace("/", "_")[0:230] + " " + subkey

                # make the filename safe
                filename = filename.replace(":", "_")
                while filename.startswith("."):
                    filename = filename[1:]

                print(f">> {subkey} {child['data']['itemType']} {title}")

                imported = True
                for collection in collections:
                    if collection in libraries:
                        path = os.path.join(
                            libraries[collection]["save_path"], filename
                        )
                        if not os.path.exists(path):
                            print(f"    {path}")
                            zot.dump(subkey, path, filename)

    return imported


def import_zotero():
    for key, library in get_zotero_libraries().items():
        # while True:
        save_root = library["save_root"]
        aleph_id = library["aleph_id"]
        if os.path.exists(save_root):
            print("Importing Zotero library {} -> {}".format(save_root, aleph_id))
            os.system(f"/Users/rob/bin/prune -f {aleph_id} -d {save_root}")
            os.system(f"alephclient crawldir -f {aleph_id} -p 1 {save_root}")
            os.system(f"/Users/rob/bin/prune -f {aleph_id} -d {save_root}")


def run_importer(sleep_interval, repeat):
    go = True
    while go:
        if fetch_from_zotero():
            import_zotero()
        if not repeat:
            go = False
        else:
            time.sleep(sleep_interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["import"], help="Command to run")
    parser.add_argument("--sleep_interval", "-s", type=int, default=30)
    parser.add_argument("--repeat", "-r", action="store_true")
    args = parser.parse_args()
    log.info("loading with {}".format(args))

    if args.command == "import":
        run_importer(
            sleep_interval=args.sleep_interval,
            repeat=args.repeat,
        )


if __name__ == "__main__":
    main()
