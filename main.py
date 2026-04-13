import time

CHAR_NAME = "Sallazzar"

# ======= CONFIG (EDITE AQUI) =======
APPLY_SIZE = True          # True = aplicar tamanho/posição abaixo | False = só borderless
TARGET_X = 0
TARGET_Y = 0
TARGET_W = 1700
TARGET_H = 1300
# ===================================


def find_window_by_title(partial_title: str):
    import win32gui

    result = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd) or ""
        if partial_title.lower() in title.lower():
            result.append((hwnd, title))

    win32gui.EnumWindows(enum_handler, None)
    return result[0] if result else (None, None)


def set_borderless(hwnd) -> None:
    import win32gui
    import win32con

    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

    # Remove título, bordas e botões padrão
    style &= ~(
        win32con.WS_CAPTION
        | win32con.WS_THICKFRAME
        | win32con.WS_MINIMIZEBOX
        | win32con.WS_MAXIMIZEBOX
        | win32con.WS_SYSMENU
    )

    # Remove bordas extras
    ex_style &= ~(
        win32con.WS_EX_DLGMODALFRAME
        | win32con.WS_EX_CLIENTEDGE
        | win32con.WS_EX_STATICEDGE
        | win32con.WS_EX_WINDOWEDGE
    )

    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

    # Força o Windows a recalcular o frame (sem mover/redimensionar)
    win32gui.SetWindowPos(
        hwnd,
        None,
        0, 0, 0, 0,
        win32con.SWP_NOZORDER
        | win32con.SWP_NOMOVE
        | win32con.SWP_NOSIZE
        | win32con.SWP_FRAMECHANGED
    )


def apply_position_and_size(hwnd, x: int, y: int, w: int, h: int) -> None:
    import win32gui
    import win32con

    # Move e redimensiona (sem mexer no Z-order)
    win32gui.SetWindowPos(
        hwnd,
        None,
        x, y, w, h,
        win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED
    )


def main():
    time.sleep(0.2)

    try:
        import win32gui
        import win32con
    except Exception:
        print("[ERRO] Falta pywin32. Instale com: pip install pywin32")
        return

    hwnd, title = find_window_by_title(CHAR_NAME)
    if not hwnd:
        print(f"[ERRO] Não encontrei janela visível com título contendo '{CHAR_NAME}'.")
        return

    # Restaura se minimizada
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    except Exception:
        pass

    # 1) Borderless
    set_borderless(hwnd)

    # 2) (Opcional) aplicar tamanho/posição escolhidos
    if APPLY_SIZE:
        apply_position_and_size(hwnd, TARGET_X, TARGET_Y, TARGET_W, TARGET_H)
        print(f"[OK] Borderless + tamanho aplicado: '{title}' -> ({TARGET_X},{TARGET_Y}) {TARGET_W}x{TARGET_H}")
    else:
        print(f"[OK] Borderless aplicado (sem alterar tamanho): '{title}'")


if __name__ == "__main__":
    main()
