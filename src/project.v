/*
 * chip-lab 내보내기 · 설계 6a45cc53-59a6-40f0-9fd6-7a438bf125e4
 * 병렬 핀 INT8 내적 가속기 N=8, 결과 16bit saturate, 클록당 1바이트 (a0,b0,a1,b1,…)
 * SPDX-License-Identifier: Apache-2.0
 *
 *   ui_in[7:0]  IN_DATA   (호스트 → 칩, IN_VALID·IN_READY 가 둘 다 1 인 클록 상승에서 받음)
 *   uio[0] in   IN_VALID
 *   uio[1] in   ABORT     (받던 벡터 폐기, ERR 켬)
 *   uio[2] in   OUT_READY
 *   uio[3] in   CHAIN     (벡터 마지막 바이트를 받을 때 1 이면 결과를 내지 않고 다음 벡터로 이어 더함)
 *   uio[4] out  IN_READY  (결과를 다 읽기 전에는 다음 벡터의 마지막 바이트만 막음)
 *   uio[5] out  OUT_VALID
 *   uio[6] out  BUSY
 *   uio[7] out  ERR
 *   uo_out      OUT_DATA  (결과 2 바이트, 하위 바이트부터, OUT_VALID·OUT_READY 상승에서 다음 바이트)
 */
`default_nettype none

module tt_um_joonsense_pin_dot_6a45cc53 (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
  wire in_ready, out_valid, busy, err_seen;
  wire [2:0] count;

  tt_um_joonsense_pin_dot_6a45cc53_core core (.clk(clk), .rst(!rst_n), .in_valid(uio_in[0]), .in_data(ui_in), .abort(uio_in[1]), .out_ready(uio_in[2]),
      .in_ready(in_ready), .out_valid(out_valid), .out_data(uo_out), .busy(busy), .err_seen(err_seen), .count(count), .chain(uio_in[3]), .load(uio_in[6]));

  assign uio_out = {err_seen, 1'b0, out_valid, in_ready, 4'b0000};
  assign uio_oe  = 8'b1011_0000;

  wire _unused = &{ena, uio_in[7], uio_in[5:4], busy, count, 1'b0};

endmodule

`default_nettype wire
