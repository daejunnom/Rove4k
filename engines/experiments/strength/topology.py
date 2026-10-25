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
