
def format_color_code(val: int | str, mode="33"):
    if mode == "33":
        return f"\033[{val}m"
    elif mode == "foregroung":
        return f"\033[38;5;{val}m"
    else:
        raise Exception(f"Unknown mode {mode}")

RED = format_color_code(31)
GRN = format_color_code(32)
ORG = format_color_code(33)
YEL = format_color_code(93)
BLD = format_color_code(1)
RES = format_color_code(0)
