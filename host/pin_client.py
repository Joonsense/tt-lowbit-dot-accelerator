# SPDX-License-Identifier: Apache-2.0
# chip-lab 병렬 핀 INT8 내적 가속기 호스트 드라이버 (MicroPython·CPython 공용).
#
# 핀 (칩 기준): ui_in = IN_DATA, uio[0] IN_VALID · uio[1] ABORT · uio[2] OUT_READY · uio[3] CHAIN (CHAIN 판만) (호스트가 구동),
#               uio[4] IN_READY · uio[5] OUT_VALID · uio[6] BUSY · uio[7] ERR, uo_out = OUT_DATA (칩이 구동).
# 한 사이클 = 호스트가 값을 올리고 → 칩 출력을 읽고 → 클록 한 번. 상승 순간에 IN_VALID·IN_READY 가 1 이면 바이트가
# 넘어가고, OUT_VALID·OUT_READY 가 1 이면 결과 바이트가 넘어간다. 그래서 읽기는 반드시 tick 전에 한다.
#
# 같은 코드를 두 곳에서 쓴다: TT 데모보드(DemoBoardPort, 수동 클록) 와 cocotb 시뮬레이션(test.py 의 CocotbPort).
# 수동 클록이라 보드에서는 느리다 (프로토콜 확인용). 클록당 1바이트 속도는 RP2040 PIO 가 필요하다 (미구현).

IN_VALID, ABORT, OUT_READY, CHAIN = 1, 2, 4, 8
LOAD = 64   # 가중치 고정판만: uio[6] 이 BUSY 출력 대신 LOAD 입력
IN_READY, OUT_VALID, BUSY, ERR = 16, 32, 64, 128


class PinDot:
    def __init__(self, port, n, width, int4=False, stationary=False, act_bits=4):
        # int4: 바이트 하나에 INT4 원소 두 개 (하위 니블이 앞 원소). 벡터 원소는 2N 개를 받는다.
        # stationary: 가중치를 load() 로 칩에 두고 x 만 보낸다 (batch). 교차판 stream·long_dot 은 쓰지 않는다.
        # act_bits 2·1 (INT4 가중치 고정판만): x 는 부호 없는 0..3 / 0..1, 바이트 하나에 4·8 개 (앞 원소가 하위 비트).
        self.port, self.n, self.width, self.int4, self.stationary = port, n, width, int4, stationary
        self.act_bits = act_bits
        self.elements = 2 * n if int4 else n
        self.nbytes = (width + 7) // 8
        self.cycles = 0

    def signed(self, raw):
        raw &= (1 << self.width) - 1
        return raw - (1 << self.width) if raw >> (self.width - 1) else raw

    def to_bytes(self, values):
        """원소 목록 → 칩에 보낼 바이트. INT4 는 두 개씩 묶는다."""
        if len(values) != self.elements:
            raise ValueError('vector length must be %d' % self.elements)
        if self.int4:
            if min(values) < -8 or max(values) > 7:
                raise ValueError('INT4 elements must be in [-8, 7]')
            return [(lo & 15) | ((hi & 15) << 4) for lo, hi in zip(values[0::2], values[1::2])]
        return [v & 255 for v in values]

    def act_bytes(self, values):
        """활성값(x) 목록 → 바이트. act_bits 4 면 to_bytes 와 같다."""
        if self.act_bits == 4:
            return self.to_bytes(values)
        if len(values) != self.elements:
            raise ValueError('vector length must be %d' % self.elements)
        top, per = (1 << self.act_bits) - 1, 8 // self.act_bits
        if min(values) < 0 or max(values) > top:
            raise ValueError('activations must be in [0, %d]' % top)
        return [sum(v << (self.act_bits * j) for j, v in enumerate(values[i:i + per])) for i in range(0, len(values), per)]

    def stream(self, vectors, limit=100000, chains=None):
        """vectors = [(a, b), ...] → 내적 결과 목록. 입력과 결과 읽기를 같은 사이클에 겹쳐 진행한다.
        chains[i] 가 참이면 i 번째 벡터는 결과를 내지 않고 다음 벡터로 이어 더한다 (CHAIN 판)."""
        chains = chains or [False] * len(vectors)
        data, flags = [], []
        for (a, b), chained in zip(vectors, chains):
            for x, y in zip(self.to_bytes(a), self.to_bytes(b)):
                data.append(x)
                data.append(y)
                flags.extend([CHAIN if chained else 0] * 2)
        return self.run(data, flags, sum(1 for chained in chains if not chained), limit)

    def load(self, weights, limit=10000):
        """가중치 고정판: 가중치 원소 N 개(INT4 는 2N)를 칩에 싣는다. 다음 load 까지 유지된다."""
        data = self.to_bytes(weights)
        self.run(data, [LOAD] * len(data), 0, limit)

    def batch(self, xs, limit=1000000, chains=None):
        """가중치 고정판: 실린 가중치와 x 벡터들의 내적을 차례로. x 한 바이트 = 원소 하나(INT4 는 둘, act_bits 2·1 은 넷·여덟)를 클록마다."""
        chains = chains or [False] * len(xs)
        data, flags = [], []
        for x, chained in zip(xs, chains):
            chunk = self.act_bytes(x)
            data.extend(chunk)
            flags.extend([CHAIN if chained else 0] * len(chunk))
        return self.run(data, flags, sum(1 for chained in chains if not chained), limit)

    def batch_dot(self, w, xs):
        """가중치 고정판, 길이 제한 없음: w·x_k 를 모든 k 에 대해. w 를 조각마다 한 번 싣고 그 조각의 x 를 모두 흘린 뒤,
        조각별 부분합을 호스트가 더한다 (정확한 정수 합. 칩 결과 폭을 넘는 부분합은 칩에서 포화되므로 조각을 짧게 둔다)."""
        size = self.elements
        pad = (-len(w)) % size
        w = list(w) + [0] * pad
        xs = [list(x) + [0] * pad for x in xs]
        totals = [0] * len(xs)
        for start in range(0, len(w), size):
            self.load(w[start:start + size])
            for k, part in enumerate(self.batch([x[start:start + size] for x in xs])):
                totals[k] += part
        return totals

    def run(self, data, flags, wanted, limit):
        results, raw, got, index = [], 0, 0, 0
        start = self.cycles   # limit 은 이 호출 기준 (누적 cycles 로 비교하면 긴 세션에서 언젠가 반드시 시간 초과)
        while len(results) < wanted or index < len(data):   # load 처럼 결과가 없는 호출도 바이트를 다 보낼 때까지
            if self.cycles - start >= limit:
                raise RuntimeError('timeout after %d cycles' % (self.cycles - start))
            valid = index < len(data)
            self.port.write(data[index] if valid else 0, ((IN_VALID | flags[index]) if valid else 0) | OUT_READY)
            status, out = self.port.read()
            self.port.tick()
            self.cycles += 1
            if valid and status & IN_READY:
                index += 1
            if status & OUT_VALID:
                raw |= out << (8 * got)
                got += 1
                if got == self.nbytes:
                    results.append(self.signed(raw))
                    raw, got = 0, 0
        self.port.write(0, OUT_READY)
        return results

    def dot(self, a, b):
        return self.stream([(a, b)])[0]

    def long_dot(self, a, b):
        """길이 제한 없는 내적 (CHAIN 판): N 개씩 잘라 마지막 조각 전까지 CHAIN, 끝 조각은 0 으로 채운다 (0 곱은 합에 영향 없음)."""
        if len(a) != len(b) or not a:
            raise ValueError('a and b must have the same non-zero length')
        pad = (-len(a)) % self.elements
        a, b = list(a) + [0] * pad, list(b) + [0] * pad
        pieces = [(a[i:i + self.elements], b[i:i + self.elements]) for i in range(0, len(a), self.elements)]
        return self.stream(pieces, chains=[True] * (len(pieces) - 1) + [False])[0]

    def abort(self):
        """받던 벡터를 버린다. ERR 가 켜져야 한다."""
        self.port.write(0, ABORT)
        self.port.tick()
        self.port.write(0, OUT_READY)
        status, _ = self.port.read()
        return bool(status & ERR)


class DemoBoardPort:
    """TT 데모보드 MicroPython SDK (ttboard). 프로젝트를 enable 한 뒤 쓴다."""

    def __init__(self, tt, stationary=False):
        self.tt = tt
        # uio[3:0] 은 RP2040 이 구동 (CHAIN 없는 판은 uio[3] 을 안 씀). 가중치 고정판은 uio[6] LOAD 도 RP2040 이 구동
        # (다른 판에서는 uio[6] 이 칩의 BUSY 출력이라 구동하면 안 된다).
        tt.uio_oe_pico.value = IN_VALID | ABORT | OUT_READY | CHAIN | (LOAD if stationary else 0)

    def write(self, data, control):
        self.tt.ui_in.value = data
        self.tt.uio_in.value = control

    def read(self):
        return int(self.tt.uio_out.value), int(self.tt.uo_out.value)

    def tick(self):
        self.tt.clock_project_once()


def main(n, width, cases):
    """데모보드 REPL 에서: import pin_client; pin_client.main(**설정) — vectors.json 의 n·acc_width·cases 를 넘긴다."""
    from ttboard.demoboard import DemoBoard
    tt = DemoBoard.get()
    chip = PinDot(DemoBoardPort(tt), n, width)
    tt.reset_project(True)
    tt.clock_project_once()
    tt.reset_project(False)
    failures = 0
    for index, (a, b, expected) in enumerate(cases):
        got = chip.dot(a, b)
        failures += got != expected
        print('%2d %s got %d expected %d' % (index, 'OK' if got == expected else 'FAIL', got, expected))
    print('%d/%d match, %d cycles' % (len(cases) - failures, len(cases), chip.cycles))
    return failures
