#!/usr/bin/env python3
import io
import shutil
import tarfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "openwrt" / "luci-app-ikuuu-checkin"
FILES = PACKAGE / "files"
CONTROL = PACKAGE / "ipk-control"
DIST = ROOT / "dist"
VERSION = "1.0.1-1"
OUTPUT = DIST / f"luci-app-ikuuu-checkin_{VERSION}_all.ipk"


def executable(path):
    value = path.as_posix()
    return "/etc/init.d/" in value or "/usr/libexec/" in value or path.name in {"postinst", "prerm"}


def tar_bytes(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz", format=tarfile.GNU_FORMAT) as archive:
        for source, archive_name in entries:
            info = archive.gettarinfo(str(source), arcname=f"./{archive_name}")
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = int(time.time())
            if source.is_file():
                info.mode = 0o755 if executable(source) else 0o644
                if archive_name == "etc/config/ikuuu-checkin":
                    info.mode = 0o600
                with source.open("rb") as handle:
                    archive.addfile(info, handle)
            else:
                info.mode = 0o755
                archive.addfile(info)
    return stream.getvalue()


def tree_entries(root):
    return [(path, path.relative_to(root).as_posix()) for path in sorted(root.rglob("*"))]


def main():
    packaged = FILES / "usr" / "libexec" / "ikuuu-checkin" / "auto_check_in_ikuuu.py"
    packaged.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "auto_check_in_ikuuu.py", packaged)
    control_archive = tar_bytes([(CONTROL / name, name) for name in ("control", "conffiles", "postinst", "prerm")])
    data_archive = tar_bytes(tree_entries(FILES))
    DIST.mkdir(parents=True, exist_ok=True)
    with tarfile.open(OUTPUT, mode="w:gz", format=tarfile.GNU_FORMAT) as archive:
        for name, payload in (("debian-binary", b"2.0\n"), ("control.tar.gz", control_archive), ("data.tar.gz", data_archive)):
            info = tarfile.TarInfo(name=f"./{name}")
            info.size = len(payload)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mtime = int(time.time())
            archive.addfile(info, io.BytesIO(payload))
    print(OUTPUT)


if __name__ == "__main__":
    main()
