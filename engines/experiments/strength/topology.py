"""Linux topology snapshots and physical-core slots, independent of engines."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import os
from pathlib import Path
import re


def parse_list(text):
    values = set()
    if not text.strip():
        return values
    for token in text.strip().split(","):
        if not re.fullmatch(r"\d+(?:-\d+)?", token):
            raise ValueError("invalid Linux CPU/node list")
        ends = [int(part) for part in token.split("-")]
        first, last = ends[0], ends[-1]
        if first > last or last - first > 1_000_000:
            raise ValueError("invalid CPU/node extent")
        values.update(range(first, last + 1))
    return values


def format_list(values):
    return ",".join(str(value) for value in sorted(values))


@dataclass(frozen=True)
class Cpu:
    id: int
    socket: int
    core: int
    node: int
    siblings: tuple[int, ...]

    @property
    def physical(self):
        return self.socket, self.core


@dataclass(frozen=True)
class Topology:
    cpus: tuple[Cpu, ...]
    allowed_cpus: tuple[int, ...]
    allowed_nodes: tuple[int, ...]
    distances: dict
    kernel: str

    def __post_init__(self):
        ids = [cpu.id for cpu in self.cpus]
        if len(ids) != len(set(ids)) or not set(self.allowed_cpus) <= set(ids):
            raise ValueError("topology CPU identities are duplicate or missing")
        for cpu in self.cpus:
            if any(type(value) is not int or value < 0 for value in (cpu.id, cpu.socket, cpu.core, cpu.node)):
                raise ValueError("topology requires observed nonnegative identities")
            if cpu.id not in cpu.siblings:
                raise ValueError("CPU is absent from its own sibling set")

    @classmethod
    def from_record(cls, value):
        return cls(tuple(Cpu(**{**row, "siblings": tuple(row["siblings"])}) for row in value["cpus"]),
                   tuple(value["allowed_cpus"]), tuple(value["allowed_nodes"]), value["distances"], value["kernel"])

    @classmethod
    def snapshot(cls, sysroot=Path("/sys"), procroot=Path("/proc")):
        if not hasattr(os, "sched_getaffinity"):
            raise RuntimeError("execution topology requires Linux CPU affinity")
        online = parse_list((sysroot / "devices/system/cpu/online").read_text())
        allowed = set(os.sched_getaffinity(0)) & online
        status = (procroot / "self/status").read_text()
        node_match = re.search(r"^Mems_allowed_list:\s*(.*)$", status, re.MULTILINE)
        if node_match is None:
            raise ValueError("effective allowed memory nodes unavailable")
        mems = parse_list(node_match[1])
        nodes, distances = {}, {}
        for path in sorted((sysroot / "devices/system/node").glob("node[0-9]*")):
            node = int(path.name[4:])
            if (path / "cpulist").exists():
                for cpu in parse_list((path / "cpulist").read_text()):
                    nodes[cpu] = node
            if (path / "distance").exists():
                distances[str(node)] = [int(value) for value in (path / "distance").read_text().split()]
        rows = []
        for cpu in sorted(allowed):
            root = sysroot / f"devices/system/cpu/cpu{cpu}/topology"
            if cpu not in nodes:
                raise ValueError("CPU has no observed NUMA node: " + str(cpu))
            rows.append(Cpu(cpu, int((root / "physical_package_id").read_text()),
                            int((root / "core_id").read_text()), nodes[cpu],
                            tuple(sorted(parse_list((root / "thread_siblings_list").read_text())))))
        return cls(tuple(rows), tuple(sorted(allowed)), tuple(sorted(mems)), distances, os.uname().release)

    @classmethod
    def snapshot_target(cls, path, *, device, inode, sysroot=Path("/sys")):
        """Read a target cgroup's effective topology, independent of our affinity.

        The caller supplies the originally owned cgroup identity. Kernel masks,
        online CPUs and that directory identity are rechecked after sampling.
        This does not authenticate the caller or source, prove hidden ancestor
        visibility, prevent external writers, or reserve CPUs or memory.
        A non-default sysroot is solely a fixture and not runtime evidence.
        """
        if os.name != "posix" or not all(hasattr(os, key) for key in ("O_DIRECTORY", "O_NOFOLLOW")):
            raise RuntimeError("target topology requires Linux no-follow cgroup access")
        path = Path(path)
        if (not path.is_absolute() or ".." in path.parts or type(device) is not int or device < 0 or
                type(inode) is not int or inode <= 0 or
                any(item.is_symlink() for item in (path, *path.parents)) or
                path.resolve(strict=True) != path):
            raise ValueError("original target cgroup identity must be a real absolute non-symlink path")
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0))
        try:
            def identity():
                stat = os.fstat(fd)
                return stat.st_dev, stat.st_ino

            def mask(name):
                file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), dir_fd=fd)
                with os.fdopen(file_fd, "rb") as stream:
                    value = stream.read(65537)
                if len(value) > 65536:
                    raise ValueError("target effective mask is too large")
                try:
                    result = parse_list(value.decode("ascii"))
                except UnicodeDecodeError as error:
                    raise ValueError("target effective mask is not ASCII") from error
                if not result or max(result) > 1_000_000:
                    raise ValueError("target effective mask is empty or out of range")
                return result

            if identity() != (device, inode):
                raise ValueError("original target cgroup identity changed")
            online_path = Path(sysroot) / "devices/system/cpu/online"
            online = parse_list(online_path.read_text())
            allowed, mems = mask("cpuset.cpus.effective"), mask("cpuset.mems.effective")
            if not allowed <= online:
                raise ValueError("target effective CPUs exceed kernel online CPUs")
            nodes, distances, observed_nodes = {}, {}, set()
            for node_path in sorted((Path(sysroot) / "devices/system/node").glob("node[0-9]*")):
                node = int(node_path.name[4:])
                observed_nodes.add(node)
                if (node_path / "cpulist").exists():
                    for cpu in parse_list((node_path / "cpulist").read_text()):
                        if cpu in nodes and nodes[cpu] != node:
                            raise ValueError("CPU is present in multiple NUMA node lists")
                        nodes[cpu] = node
                if (node_path / "distance").exists():
                    distances[str(node)] = [int(value) for value in (node_path / "distance").read_text().split()]
            if not mems <= observed_nodes:
                raise ValueError("target effective memory nodes are not present in sysfs")
            rows = []
            for cpu in sorted(allowed):
                root = Path(sysroot) / f"devices/system/cpu/cpu{cpu}/topology"
                if cpu not in nodes:
                    raise ValueError("CPU has no observed NUMA node: " + str(cpu))
                rows.append(Cpu(cpu, int((root / "physical_package_id").read_text()),
                                int((root / "core_id").read_text()), nodes[cpu],
                                tuple(sorted(parse_list((root / "thread_siblings_list").read_text())))))
            after = path.stat(follow_symlinks=False)
            if (identity() != (device, inode) or (after.st_dev, after.st_ino) != (device, inode) or
                    any(item.is_symlink() for item in (path, *path.parents)) or
                    allowed != mask("cpuset.cpus.effective") or mems != mask("cpuset.mems.effective") or
                    online != parse_list(online_path.read_text())):
                raise ValueError("target cgroup identity, effective masks or online CPUs changed during observation")
            return cls(tuple(rows), tuple(sorted(allowed)), tuple(sorted(mems)), distances, os.uname().release)
        finally:
            os.close(fd)

    def to_record(self):
        return asdict(self)


@dataclass(frozen=True)
class Slot:
    id: str
    cpus: tuple[int, ...]
    physical_cores: tuple[tuple[int, int], ...]
    memory_nodes: tuple[int, ...]
    workers: int
    smt: bool
    policy: str = "inherit"

    def to_record(self):
        return asdict(self)


def plan_p192_slot(topology, *, policy="inherit"):
    """Plan one full 192-vCPU SMT slot from the observed allowed topology.

    No cores are reserved for a controller: any controller must share this
    slot and account for its interference separately. A slot is a requested
    arrangement, not evidence that affinity or memory policy was applied.
    """
    if policy not in ("inherit", "default", "interleave"):
        raise ValueError("invalid P192 memory policy")
    allowed = set(topology.allowed_cpus)
    if len(topology.allowed_cpus) != 192 or len(allowed) != 192:
        raise ValueError("P192 requires exactly 192 distinct allowed logical CPUs")
    allowed_nodes = set(topology.allowed_nodes)
    selected = [cpu for cpu in topology.cpus if cpu.id in allowed]
    if len(selected) != 192 or any(cpu.node not in allowed_nodes for cpu in selected):
        raise ValueError("P192 CPU or NUMA node is outside its allowed envelope")
    by_core = defaultdict(list)
    for cpu in selected:
        by_core[cpu.physical].append(cpu)
    if len(by_core) != 96:
        raise ValueError("P192 requires 96 distinct physical cores")
    for siblings in by_core.values():
        ids = {cpu.id for cpu in siblings}
        if (len(siblings) != 2 or len({cpu.node for cpu in siblings}) != 1 or
                any(len(cpu.siblings) != 2 or set(cpu.siblings) != ids for cpu in siblings)):
            raise ValueError("P192 requires two mutually observed SMT siblings per core")
    return Slot("slot-000", tuple(sorted(allowed)), tuple(sorted(by_core)),
                tuple(sorted({cpu.node for cpu in selected})), 192, True, policy)


def plan_slots(topology, physical, workers, *, reserve_physical=8, max_slots=None, policy="inherit"):
    if physical not in (4, 8, 28, 96) or workers not in (physical, physical * 2):
        raise ValueError("unsupported explicit physical/worker profile")
    if type(reserve_physical) is not int or reserve_physical < 0 or policy not in ("inherit", "default", "interleave"):
        raise ValueError("invalid reserve or memory policy")
    cores = defaultdict(list)
    allowed = set(topology.allowed_cpus)
    nodes_allowed = set(topology.allowed_nodes)
    for cpu in topology.cpus:
        if cpu.id in allowed and cpu.node in nodes_allowed:
            cores[cpu.physical].append(cpu)
    smt = workers == physical * 2
    by_node = defaultdict(list)
    for key, siblings in sorted(cores.items()):
        siblings.sort(key=lambda cpu: cpu.id)
        if len({cpu.node for cpu in siblings}) != 1:
            raise ValueError("siblings disagree about their memory node")
        if len(siblings) < (2 if smt else 1):
            continue
        by_node[siblings[0].node].append((key, tuple(cpu.id for cpu in siblings[:2 if smt else 1])))
    if sum(map(len, by_node.values())) < physical + reserve_physical:
        raise ValueError("insufficient physical cores after controller reserve")
    # Reserve whole physical cores. For node-local small slots, avoid making
    # every node a partial slot (e.g. eight 12-core nodes minus one each would
    # waste 24 cores). Maximise actual complete slots, then balance reserve.
    ordered_nodes = sorted(by_node)
    if physical in (4, 8):
        choices = {0: (0, 0, ())}
        for node in ordered_nodes:
            updated = {}
            for used_reserve, (capacity, balance, plan) in choices.items():
                for count in range(min(len(by_node[node]), reserve_physical - used_reserve) + 1):
                    score = (capacity + (len(by_node[node]) - count) // physical,
                             balance - count * count, plan + (count,))
                    used = used_reserve + count
                    if used not in updated or score[:2] > updated[used][:2]:
                        updated[used] = score
            choices = updated
        reserve = choices[reserve_physical][2]
        for node, count in zip(ordered_nodes, reserve):
            del by_node[node][:count]
    else:
        for index in range(reserve_physical):
            candidates = [node for node in ordered_nodes if by_node[node]]
            if not candidates:
                raise ValueError("cannot reserve controller cores")
            node = candidates[index % len(candidates)]
            by_node[node].pop(0)
    slots = []
    if physical in (4, 8):
        while any(len(values) >= physical for values in by_node.values()):
            for node in ordered_nodes:
                values = by_node[node]
                if len(values) < physical:
                    continue
                selected, by_node[node] = values[:physical], values[physical:]
                slots.append(Slot(f"slot-{len(slots):03d}", tuple(sorted(cpu for _, cpus in selected for cpu in cpus)),
                                  tuple(key for key, _ in selected), (node,), workers, smt, policy))
    else:
        # Every slot sees the same node count and a balanced physical envelope.
        while True:
            base, extra = divmod(physical, len(ordered_nodes))
            counts = {node: base for node in ordered_nodes}
            for offset in range(extra):
                counts[ordered_nodes[(len(slots) * max(extra, 1) + offset) % len(ordered_nodes)]] += 1
            if any(len(by_node[node]) < count for node, count in counts.items()):
                break
            selected = []
            for node, count in counts.items():
                selected.extend(by_node[node][:count])
                del by_node[node][:count]
            slots.append(Slot(f"slot-{len(slots):03d}", tuple(sorted(cpu for _, cpus in selected for cpu in cpus)),
                              tuple(key for key, _ in selected), tuple(node for node in ordered_nodes if counts[node]),
                              workers, smt, policy))
    if max_slots is not None:
        if type(max_slots) is not int or max_slots < 1:
            raise ValueError("positive slot limit required")
        slots = slots[:max_slots]
    if not slots:
        raise ValueError("no homogeneous slot fits this topology")
    used = set()
    for slot in slots:
        physical_set = set(slot.physical_cores)
        if len(physical_set) != physical or used & physical_set or not set(slot.cpus) <= allowed:
            raise ValueError("overlapping or invalid physical slot")
        used |= physical_set
    return tuple(slots)
