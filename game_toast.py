"""Non-interactive, temporary desktop game notification."""
import tkinter as tk
class GameToast:
    def __init__(self,root,text):
        self.window=tk.Toplevel(root);self.window.withdraw();self.window.overrideredirect(True)
        self.window.attributes('-topmost',True);self.window.configure(bg='#18252e')
        tk.Label(self.window,text=text,bg='#18252e',fg='#d6eafa',font=('Segoe UI',14,'bold'),padx=22,pady=14).pack()
        self.window.update_idletasks();width=self.window.winfo_reqwidth()
        self.window.geometry(f'+{max(0,(root.winfo_screenwidth()-width)//2)}+100')
        self.window.deiconify()
        self.window.after(4500,self.window.destroy)
