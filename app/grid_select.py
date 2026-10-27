"""Logic chọn thẻ trong lưới, viết thuần Python để kiểm tra được mà không cần giao diện.

Quy tắc giống Windows Explorer:
- Nhấn thường: chỉ chọn thẻ đó. Nếu thẻ đó đã nằm trong nhóm đang chọn thì giữ nguyên nhóm
  (để kéo cả nhóm); khi thả chuột mà không kéo thì thu về còn một thẻ.
- Ctrl + nhấn: bật/tắt thẻ đó trong nhóm.
- Shift + nhấn: chọn cả dãy từ thẻ neo đến thẻ vừa nhấn.
"""


def press_selection(selected, row, anchor, ctrl, shift):
    """Trả về (tập hàng được chọn sau khi nhấn, hàng neo mới)."""
    selected = set(selected)
    if ctrl:
        return selected ^ {row}, row
    if shift and anchor is not None and anchor >= 0:
        lo, hi = sorted((anchor, row))
        return set(range(lo, hi + 1)), anchor
    if row in selected:
        return selected, row
    return {row}, row


def release_selection(selected, row, pressed_row, ctrl, shift):
    """Sau khi thả chuột mà không kéo: thu nhóm về đúng thẻ vừa bấm (nếu không Ctrl/Shift)."""
    selected = set(selected)
    if ctrl or shift:
        return selected
    if row == pressed_row and len(selected) > 1:
        return {row}
    return selected
