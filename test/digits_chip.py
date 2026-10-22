# S3 응용 시연 (cocotb 모듈): digits.json 의 양자화 분류 한 층을 칩(RTL 또는 게이트 넷리스트)에 돌린다.
# 클래스마다 길이 64 내적을 호스트 드라이버 long_dot 으로 (N=8 칩이면 CHAIN 8조각). 바이어스·argmax 는 호스트.
# 합격: 칩 내적이 파이썬 INT8 계산과 비트 단위로 모두 같다. 정확도는 기록만 한다.
import json
import os

import cocotb
from cocotb.task import bridge
from cocotb.triggers import FallingEdge

from test import N, WIDTH, CocotbPort, pin_client, reset

try:
    from test import INT4
except ImportError:
    INT4 = False
try:
    from test import OPS as _stationary_program   # noqa: F401  가중치 고정판 test.py 에만 있다
    STATIONARY = True
except ImportError:
    STATIONARY = False
try:
    from test import ACT_BITS   # S7 활성값 2·1비트판
except ImportError:
    ACT_BITS = 4
NAME = f'digits-int4-a{ACT_BITS}.json' if ACT_BITS != 4 else ('digits-int4.json' if INT4 else 'digits.json')
DATA = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), NAME)))
LIMIT = int(os.environ.get('DIGITS_LIMIT', len(DATA['labels'])))


@cocotb.test()
async def test_digits_layer_on_chip(dut):
    await reset(dut)
    await FallingEdge(dut.clk)
    chip = pin_client.PinDot(CocotbPort(dut), N, WIDTH, int4=INT4, stationary=STATIONARY, act_bits=ACT_BITS)
    mismatches, correct = 0, 0
    if STATIONARY:   # 배치: 클래스마다 가중치를 조각으로 한 번씩 싣고 이미지 전부를 흘린다
        xs = DATA['inputs'][:LIMIT]
        by_class = [await bridge(chip.batch_dot)(DATA['weights'][c], xs) for c in range(10)]
        all_dots = [[by_class[c][k] for c in range(10)] for k in range(LIMIT)]
    else:
        long_dot = bridge(chip.long_dot)
        all_dots = []
        for index in range(LIMIT):
            all_dots.append([await long_dot(DATA['weights'][c], DATA['inputs'][index]) for c in range(10)])
    for index, dots in enumerate(all_dots):
        mismatches += sum(g != w for g, w in zip(dots, DATA['dots'][index]))
        logits = [d + bias for d, bias in zip(dots, DATA['bias'])]
        correct += logits.index(max(logits)) == DATA['labels'][index]
    accuracy = correct / LIMIT
    summary = {'int4': INT4, 'stationary': STATIONARY, 'act_bits': ACT_BITS, 'samples': LIMIT, 'dot_products': LIMIT * 10, 'mismatches': mismatches, 'chip_accuracy': accuracy,
               'int8_accuracy_python': DATA['int8_accuracy'], 'float_accuracy': DATA['float_accuracy'], 'cycles': chip.cycles}
    dut._log.info('DIGITS ' + json.dumps(summary))
    with open('digits_result.json', 'w') as handle:
        json.dump(summary, handle)
    assert mismatches == 0, f'칩 내적 {mismatches}개가 파이썬 INT8 계산과 다름'
