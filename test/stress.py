# chip-lab 게이트 수준 스트레스 (가중치 고정판). 내보낸 프로젝트의 test/ 에 stress.py 로 복사하고
# Makefile 의 COCOTB_TEST_MODULES 에 stress 를 더해 쓴다. 칩 쪽 기대값은 파이썬 정수 계산.
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer

from test import INT4, N, NBYTES, WIDTH, signed

try:
    from test import ACT_BITS   # 활성값 2·1비트판 (S7)
except ImportError:
    ACT_BITS = 4

IN_VALID, ABORT, OUT_READY, CHAIN, LOAD = 1, 2, 4, 8, 64
IN_READY_BIT, OUT_VALID_BIT, ERR_BIT = 4, 5, 7
LOW, HIGH = (-8, 7) if INT4 else (-128, 127)
ELEMENTS = 2 * N if INT4 else N
LIMIT = (1 << (WIDTH - 1)) - 1
X_LOW, X_HIGH = (LOW, HIGH) if ACT_BITS == 4 else (0, (1 << ACT_BITS) - 1)
PER = 8 // ACT_BITS
X_BYTES = ELEMENTS // PER if INT4 else N


def pack(values):
    if not INT4:
        return [v & 255 for v in values]
    return [(lo & 15) | ((hi & 15) << 4) for lo, hi in zip(values[0::2], values[1::2])]


def pack_x(values):
    if ACT_BITS == 4:
        return pack(values)
    return [sum(v << (ACT_BITS * j) for j, v in enumerate(values[i:i + PER])) for i in range(0, len(values), PER)]


def sat(value):
    return max(-LIMIT - 1, min(LIMIT, value))


class Bench:
    def __init__(self, dut, seed):
        self.dut, self.rng = dut, random.Random(seed)
        self.ctrl, self.got, self.stall = 0, [], 0.0
        self.raw, self.count = 0, 0

    def out(self, bit):
        return (self.dut.uio_out.value.to_unsigned() >> bit) & 1

    def drive(self, data=None):
        if data is not None:
            self.dut.ui_in.value = data & 0xFF
        self.dut.uio_in.value = self.ctrl

    async def start(self):
        cocotb.start_soon(Clock(self.dut.clk, 10, unit="us").start())
        self.dut.ena.value = 1
        await self.reset()
        cocotb.start_soon(self.reader())

    async def reset(self):
        self.ctrl = 0
        self.drive(0)
        self.dut.rst_n.value = 0
        await ClockCycles(self.dut.clk, 3)
        self.dut.rst_n.value = 1
        self.raw, self.count = 0, 0
        await FallingEdge(self.dut.clk)

    async def reader(self):
        while True:
            await FallingEdge(self.dut.clk)
            ready = self.rng.random() >= self.stall
            self.ctrl = (self.ctrl | OUT_READY) if ready else (self.ctrl & ~OUT_READY)
            self.drive()
            await Timer(1, unit="us")
            if ready and self.out(OUT_VALID_BIT) and self.dut.rst_n.value:
                self.raw |= self.dut.uo_out.value.to_unsigned() << (8 * self.count)
                self.count += 1
                if self.count == NBYTES:
                    self.got.append(signed(self.raw, WIDTH))
                    self.raw, self.count = 0, 0

    async def push(self, byte, flags=0, gap=0.0):
        while self.rng.random() < gap:
            await FallingEdge(self.dut.clk)
        self.ctrl = (self.ctrl & OUT_READY) | IN_VALID | flags
        self.drive(byte)
        while True:
            await Timer(2, unit="us")
            ready = self.out(IN_READY_BIT)
            await FallingEdge(self.dut.clk)
            if ready:
                break
        self.ctrl &= OUT_READY
        self.drive()

    async def load(self, w, gap=0.0):
        for byte in pack(w):
            await self.push(byte, LOAD, gap)

    async def x(self, values, chain=False, gap=0.0):
        for byte in pack_x(values):
            await self.push(byte, CHAIN if chain else 0, gap)

    async def drain(self, want):
        for _ in range(4000):
            if len(self.got) >= want:
                return
            await FallingEdge(self.dut.clk)
        raise AssertionError(f"결과 {len(self.got)}/{want} 개만 도착")

    async def abort(self):
        self.ctrl |= ABORT
        self.drive()
        await FallingEdge(self.dut.clk)
        self.ctrl &= ~ABORT
        self.drive()
        await Timer(2, unit="us")
        return self.out(ERR_BIT)

    def rand(self):
        return [self.rng.randint(LOW, HIGH) for _ in range(ELEMENTS)]

    def rand_x(self):
        return [self.rng.randint(X_LOW, X_HIGH) for _ in range(ELEMENTS)]


@cocotb.test()
async def batches_reloads_gaps_backpressure(dut):
    """가중치 20번 다시 싣고 묶음마다 x 20개, 입력 공백·출력 역압력 무작위 (총 400 벡터)."""
    t = Bench(dut, 2026)
    t.stall = 0.3
    await t.start()
    want = []
    for _ in range(20):
        w = t.rand()
        await t.load(w, gap=0.25)
        for _ in range(20):
            xv = t.rand_x()
            want.append(sat(sum(a * b for a, b in zip(w, xv))))
            await t.x(xv, gap=0.25)
    await t.drain(len(want))
    assert t.got == want, f"불일치 {sum(g != w for g, w in zip(t.got, want))}건"


@cocotb.test()
async def chain_random_lengths(dut):
    t = Bench(dut, 41)
    t.stall = 0.3
    await t.start()
    want = []
    for _ in range(25):
        w = t.rand()
        await t.load(w)
        group = [t.rand_x() for _ in range(t.rng.randint(1, 40))]
        want.append(sat(sum(a * b for xv in group for a, b in zip(w, xv))))
        for index, xv in enumerate(group):
            await t.x(xv, chain=index < len(group) - 1, gap=0.25)
    await t.drain(len(want))
    assert t.got == want, f"불일치 {sum(g != w for g, w in zip(t.got, want))}건"


@cocotb.test()
async def abort_and_reset_recovery(dut):
    """x 도중 ABORT → 다음 x 는 처음부터 (가중치는 그대로), 가중치 싣는 도중 ABORT → 다시 실은 가중치로, 중간 리셋."""
    t = Bench(dut, 11)
    await t.start()
    w = t.rand()
    await t.load(w)
    for round_ in range(20):
        part = pack_x(t.rand_x())[: t.rng.randint(1, max(1, X_BYTES - 1))]
        for byte in part if X_BYTES > 1 else []:
            await t.push(byte)
        assert await t.abort(), "ABORT 뒤 ERR 없음"
        if round_ % 5 == 4:   # 가중치 싣는 도중 ABORT: 처음부터 다시 싣는다
            w = t.rand()
            for byte in pack(w)[: max(1, N // 2)]:
                await t.push(byte, LOAD)
            await t.abort()
            await t.load(w)
        before = len(t.got)
        xv = t.rand_x()
        await t.x(xv)
        await t.drain(before + 1)
        assert t.got[-1] == sat(sum(a * b for a, b in zip(w, xv))), f"ABORT 뒤 {t.got[-1]}"
        assert not t.out(ERR_BIT), "ERR 미해제"
    await t.reset()
    t.got.clear()
    w = t.rand()
    await t.load(w)
    xv = t.rand_x()
    await t.x(xv)
    await t.drain(1)
    assert t.got == [sat(sum(a * b for a, b in zip(w, xv)))], "리셋 뒤 결과 틀림"
