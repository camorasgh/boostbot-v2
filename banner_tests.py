import os
import ctypes
# Ty chatgpt for the virtualization thingy
class Banner:
    
    def __init__(self):
        self.banner = r"""
 ▄▀▀▄ ▄▀▀▄  ▄▀▀▀▀▄   ▄▀▀▄▀▀▀▄  ▄▀▀▀█▀▀▄  ▄▀▀█▄▄▄▄  ▄▀▀▄  ▄▀▄ 
█   █    █ █      █ █   █   █ █    █  ▐ ▐  ▄▀   ▐ █    █   █ 
▐  █    █  █      █ ▐  █▀▀█▀  ▐   █       █▄▄▄▄▄  ▐     ▀▄▀  
   █   ▄▀  ▀▄    ▄▀  ▄▀    █     █        █    ▌       ▄▀ █  
    ▀▄▀      ▀▀▀▀   █     █    ▄▀        ▄▀▄▄▄▄       █  ▄▀  
                    ▐     ▐   █          █    ▐     ▄▀  ▄▀   
                              ▐          ▐         █    ▐    
                              
 """
        self.links = "[https://discord.gg/camora]    [https://discord.gg/borgo]"

    def enable_virtual_terminal(self):
        if os.name == 'nt':
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x4)

    def print_banner(self):
        self.enable_virtual_terminal()
        terminal_size = os.get_terminal_size()
        self.terminal_size = terminal_size
        banner_lines = self.banner.split("\n")
        gradient_purple = [53, 55, 56, 57, 93, 129, 165, 201]

        for i, line in enumerate(banner_lines):
            color_index = gradient_purple[i % len(gradient_purple)]
            print(f"\033[38;5;{color_index}m{line.center(terminal_size.columns)}")

        self.print_alternating_color_text(self.links, (terminal_size.columns - len(self.links)) // 2)
        print("\033[0m")

    def print_alternating_color_text(self, text, center):
        color1, color2 = 93 #, 57
        for i, char in enumerate(text.center(self.terminal_size.columns)):
            color_code = color1 if i % 2 == 0 else color2
            print(f"\033[38;5;{color_code}m{char}", end="")

# Example usage
banner = Banner()
banner.print_banner()
