import torch
from .kernel import sparse_ops
from .layout import SparseLayout
from typing import Any, Tuple, Optional


class SparseMatMul(torch.autograd.Function):
    @staticmethod
    def forward(ctx: Any,
                a: torch.Tensor,
                b: torch.Tensor,
                mode: str,
                layout: SparseLayout,
                trans_a: bool = False,
                trans_b: bool = False) -> torch.Tensor:
        ctx.save_for_backward(a, b)
        ctx.mode, ctx.layout = mode, layout
        ctx.trans_a, ctx.trans_b = trans_a, trans_b

        return sparse_ops.batched_sparse_matmul(
            a, b, mode,
            layout.row_blocks, layout.row_table,
            layout.col_blocks, layout.col_table,
            trans_a, trans_b)

    @staticmethod
    def backward(ctx: Any, dc: torch.Tensor
                 ) -> Tuple[Optional[torch.Tensor], ...]:
        a, b = ctx.saved_tensors
        mode, layout = ctx.mode, ctx.layout
        trans_a, trans_b = ctx.trans_a, ctx.trans_b

        # Note that all tensors in sparse operations must be contiguous.
        if not dc.is_contiguous():
            dc = dc.contiguous()

        da, db = None, None

        if ctx.needs_input_grad[0]:
            if trans_a:
                da = sparse_ops.batched_sparse_matmul(
                    b, dc, mode[1] + mode[2] + mode[0],
                    layout.row_blocks, layout.row_table,
                    layout.col_blocks, layout.col_table,
                    trans_b, True)
            else:
                da = sparse_ops.batched_sparse_matmul(
                    dc, b, mode[1] + mode[0] + mode[2],
                    layout.row_blocks, layout.row_table,
                    layout.col_blocks, layout.col_table,
                    False, not trans_b)

        if ctx.needs_input_grad[1]:
            if trans_b:
                db = sparse_ops.batched_sparse_matmul(
                    dc, a, mode[2] + mode[0] + mode[1],
                    layout.row_blocks, layout.row_table,
                    layout.col_blocks, layout.col_table,
                    True, trans_a)
            else:
                db = sparse_ops.batched_sparse_matmul(
                    a, dc, mode[2] + mode[1] + mode[0],
                    layout.row_blocks, layout.row_table,
                    layout.col_blocks, layout.col_table,
                    not trans_a, False)

        return da, db, None, None, None, None


matmul = SparseMatMul.apply