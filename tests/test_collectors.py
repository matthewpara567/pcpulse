from pcpulse import collect_snapshot


def test_snapshot_has_core_fields():
    s=collect_snapshot()
    assert s.schema_version=="1.0"
    assert s.os and s.architecture


def test_empty_and_optical_drives_are_skipped(monkeypatch):
    from collections import namedtuple

    import psutil

    part = namedtuple("part", "device mountpoint fstype opts")
    fake = [
        part("C:\\", "C:\\", "NTFS", "rw,fixed"),
        part("D:\\", "D:\\", "", "rw,removable"),
        part("E:\\", "E:\\", "CDFS", "ro,cdrom"),
    ]
    monkeypatch.setattr(psutil, "disk_partitions", lambda all=False: fake)
    monkeypatch.setattr(
        psutil, "disk_usage", lambda path: namedtuple("u", "total free percent")(100, 50, 50.0)
    )
    assert [d.path for d in collect_snapshot().disks] == ["C:\\"]
