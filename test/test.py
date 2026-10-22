# SPDX-License-Identifier: Apache-2.0
# chip-lab 내보내기: 기대값은 chip-lab 고정 기준 모델(reference-1.0, seed 42)에서 계산했다.

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer


async def reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

N = 8
INTERVAL = 2
INT4 = True
ACT_BITS = 1
ACT_RANGE = (0, 1)
X_BYTES = 2
NBYTES = 2
WIDTH = 16
OPS = [[0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 0, 0], [0, 0, 0], [255, 0, 0], [255, 0, 0], [255, 0, 0], [255, 0, 0], [0, 0, 0], [0, 0, 0], [135, 1, 0], [135, 1, 0], [135, 1, 0], [135, 1, 0], [135, 1, 0], [135, 1, 0], [135, 1, 0], [135, 1, 0], [255, 0, 0], [255, 0, 0], [170, 0, 0], [170, 0, 0], [205, 0, 0], [73, 0, 0], [188, 0, 0], [133, 0, 0], [4, 1, 0], [47, 1, 0], [249, 1, 0], [41, 1, 0], [4, 1, 0], [234, 1, 0], [226, 1, 0], [71, 1, 0], [229, 0, 0], [9, 0, 0], [146, 0, 0], [204, 0, 0], [15, 0, 0], [1, 0, 0], [31, 0, 0], [67, 0, 0], [213, 1, 0], [96, 1, 0], [175, 1, 0], [182, 1, 0], [137, 1, 0], [250, 1, 0], [93, 1, 0], [119, 1, 0], [210, 0, 0], [79, 0, 0], [92, 0, 0], [59, 0, 0], [196, 0, 0], [58, 0, 0], [178, 0, 0], [24, 0, 0], [93, 1, 0], [216, 1, 0], [82, 1, 0], [15, 1, 0], [189, 1, 0], [148, 1, 0], [247, 1, 0], [110, 1, 0], [195, 0, 0], [61, 0, 0], [182, 0, 0], [159, 0, 0], [38, 0, 0], [208, 0, 0], [190, 0, 0], [219, 0, 0], [26, 1, 0], [15, 1, 0], [34, 1, 0], [202, 1, 0], [252, 1, 0], [196, 1, 0], [174, 1, 0], [85, 1, 0], [103, 0, 0], [123, 0, 0], [229, 0, 0], [254, 0, 0], [28, 0, 0], [57, 0, 0], [245, 0, 0], [179, 0, 0], [36, 1, 0], [120, 1, 0], [210, 1, 0], [231, 1, 0], [3, 1, 0], [2, 1, 0], [128, 1, 0], [174, 1, 0], [118, 0, 0], [234, 0, 0], [167, 0, 0], [146, 0, 0], [33, 0, 0], [250, 0, 0], [57, 0, 0], [69, 0, 0], [154, 1, 0], [29, 1, 0], [97, 1, 0], [107, 1, 0], [65, 1, 0], [112, 1, 0], [166, 1, 0], [89, 1, 0], [67, 0, 0], [110, 0, 0], [107, 0, 0], [78, 0, 0], [110, 1, 0], [55, 1, 0], [134, 1, 0], [217, 1, 0], [195, 1, 0], [144, 1, 0], [157, 1, 0], [243, 1, 0], [225, 0, 1], [230, 0, 1], [88, 0, 1], [224, 0, 1], [25, 0, 0], [107, 0, 0], [119, 1, 0], [119, 1, 0], [119, 1, 0], [119, 1, 0], [119, 1, 0], [119, 1, 0], [119, 1, 0], [119, 1, 0], [255, 0, 1], [255, 0, 1], [255, 0, 1], [255, 0, 1], [255, 0, 1], [255, 0, 1], [255, 0, 1], [255, 0, 1], [255, 0, 0], [255, 0, 0], [231, 1, 0], [177, 1, 0], [165, 1, 0], [68, 1, 0], [26, 1, 0], [76, 1, 0], [111, 1, 0], [31, 1, 0], [28, 0, 0], [121, 0, 0], [248, 1, 0], [74, 1, 0], [3, 1, 0], [14, 1, 0], [39, 1, 0], [221, 1, 0], [163, 1, 0], [73, 1, 0], [93, 0, 1], [89, 0, 1], [139, 0, 0], [106, 0, 0]]
WANT = [0, 0, 0, 0, -8, -64, 11, -4, -1, -2, 9, 9, -18, -3, -6, -19, 1, 6, 13, -3, -22, -14, -15, -21, -16, -13, -15, 13, -20, -7, -37, 560, 3, -28]
IN_VALID, OUT_READY, CHAIN, LOAD = 1, 4, 8, 64


def pin(dut, bit):
    return (dut.uio_out.value.to_unsigned() >> bit) & 1


def signed(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


async def collect(dut, got, done_at):
    raw, count, cycle = 0, 0, 0
    while True:
        await FallingEdge(dut.clk)
        cycle += 1
        if pin(dut, 5):
            raw |= dut.uo_out.value.to_unsigned() << (8 * count)
            count += 1
            if count == NBYTES:
                got.append(signed(raw, WIDTH))
                done_at.append(cycle)
                raw, count = 0, 0


async def drive(dut, ops):
    index = 0
    while index < len(ops):
        data, load, chain = ops[index]
        dut.ui_in.value = data & 0xFF
        dut.uio_in.value = IN_VALID | OUT_READY | (LOAD if load else 0) | (CHAIN if chain else 0)
        await Timer(1, unit="us")
        ready = pin(dut, 4)
        await FallingEdge(dut.clk)
        if ready:
            index += 1
    dut.uio_in.value = OUT_READY


@cocotb.test()
async def test_weight_stationary_program(dut):
    await reset(dut)
    await FallingEdge(dut.clk)
    got, done_at = [], []
    cocotb.start_soon(collect(dut, got, done_at))
    await drive(dut, OPS)
    for _ in range(4 * NBYTES + 12):
        await FallingEdge(dut.clk)
    assert got == WANT, f"{got} != {WANT}"
    # 쉼 없는 간격: 같은 가중치로 x 벡터 4개를 연달아 → 결과 간격 = INTERVAL (x 바이트 X_BYTES 개)
    got.clear(); done_at.clear()
    xs = [op for op in OPS if not op[1]][:4 * X_BYTES]
    await drive(dut, [(op[0], 0, 0) for op in xs])
    for _ in range(4 * NBYTES + 12):
        await FallingEdge(dut.clk)
    gaps = {b - a for a, b in zip(done_at, done_at[1:])}
    assert gaps == {INTERVAL}, f"벡터 간격 {gaps} (기대 {INTERVAL})"


import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "host"))
import pin_client  # noqa: E402
from cocotb.task import bridge, resume  # noqa: E402


class CocotbPort:
    def __init__(self, dut):
        self.dut = dut

    @resume
    async def write(self, data, control):
        self.dut.ui_in.value = data
        self.dut.uio_in.value = control

    @resume
    async def read(self):
        await Timer(1, unit="us")
        return self.dut.uio_out.value.to_unsigned(), self.dut.uo_out.value.to_unsigned()

    @resume
    async def tick(self):
        await FallingEdge(self.dut.clk)


def rand(rng, length):
    low, high = (-8, 7) if INT4 else (-128, 127)
    return [rng.randint(low, high) for _ in range(length)]


def rand_x(rng, length):
    return [rng.randint(*ACT_RANGE) for _ in range(length)]


@cocotb.test()
async def test_host_batch(dut):
    await reset(dut)
    await FallingEdge(dut.clk)
    chip = pin_client.PinDot(CocotbPort(dut), N, WIDTH, int4=INT4, stationary=True, act_bits=ACT_BITS)
    rng = random.Random(42)
    lim = (1 << (WIDTH - 1)) - 1
    for _ in range(3):
        w = rand(rng, chip.elements)
        xs = [rand_x(rng, chip.elements) for _ in range(20)]
        await bridge(chip.load)(w)
        got = await bridge(chip.batch)(xs)
        assert got == [max(-lim - 1, min(lim, sum(a * b for a, b in zip(w, x)))) for x in xs]


@cocotb.test()
async def test_host_batch_dot_long(dut):
    await reset(dut)
    await FallingEdge(dut.clk)
    chip = pin_client.PinDot(CocotbPort(dut), N, WIDTH, int4=INT4, stationary=True, act_bits=ACT_BITS)
    rng = random.Random(43)
    for length in (100, 784):
        w = rand(rng, length)
        xs = [rand_x(rng, length) for _ in range(5)]
        got = await bridge(chip.batch_dot)(w, xs)
        assert got == [sum(a * b for a, b in zip(w, x)) for x in xs], f"길이 {length}"
