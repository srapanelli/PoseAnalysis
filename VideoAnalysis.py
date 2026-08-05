import customtkinter

from customtkinter import filedialog

class PoseAnalysisApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("500x200")

        self.button = customtkinter.CTkButton(self, text="Analize", command=self.analysis_callback)
        self.button.pack(padx=20,pady=20)

        self.button = customtkinter.CTkButton(self, text="Upload File", command=self.selectfile)
        self.button.pack(padx=20,pady=20)

    def analysis_callback(self):
        print("Analizing...")

    def selectfile(self):
        filename = filedialog.askopenfilename()
        print(filename)

app = PoseAnalysisApp()
app.mainloop()
