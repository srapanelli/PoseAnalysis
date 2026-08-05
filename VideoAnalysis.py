import customtkinter as ctk

from tkinter import filedialog, messagebox

class PoseAnalysisApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pose Analysis")
        self.geometry("1500x800")
        self.minsize(1000,800)

        self.video_path = None

        self.grid_columnconfigure(0, weight=0) # Upload controls left
        self.grid_columnconfigure(1, weight=1) # Visualize pose right
        self.grid_rowconfigure(0, weight=1)

        self.build_left_panel()
        self.build_right_panel()

    def build_left_panel(self):
        self.left_panel = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsw")
        self.left_panel.grid_propagate(False)
        self.left_panel.grid_rowconfigure(5, weight=1)

        title = ctk.CTkLabel(
            self.left_panel,
            text="Video Input",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.grid(row=0, column=0, padx=20, pady=(25, 10), sticky="w")

        self.file_label = ctk.CTkLabel(
            self.left_panel,
            text="Select a file below",
            wraplength=210,
            justify="left",
        )
        self.file_label.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        self.upload_button = ctk.CTkButton(
            self.left_panel,
            text="Upload File",
            height=40,
            command=self.upload_video,
        )
        self.upload_button.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.analyze_button = ctk.CTkButton(
            self.left_panel,
            text="Analyze",
            height=40,
            command=self.analyze_video,
            state="disabled",
        )
        self.analyze_button.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(
            self.left_panel,
            text="Status: waiting for input",
            wraplength=210,
            justify="left",
        )
        self.status_label.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="w")

    def build_right_panel(self):
        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        self.right_panel.grid_rowconfigure(1, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        top_controls = ctk.CTkFrame(self.right_panel)
        top_controls.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        top_controls.grid_columnconfigure((0, 1, 2), weight=1)

        self.prev_button = ctk.CTkButton(
            top_controls,
            text="Prev",
            command=self.prev_frame,
            fg_color="gray"
        )
        self.prev_button.grid(row=0, column=0, padx=8, pady=10, sticky="ew")

        self.play_button = ctk.CTkButton(
            top_controls,
            text="Play",
            command=self.toggle_play,
            fg_color="green"
        )
        self.play_button.grid(row=0, column=1, padx=8, pady=10, sticky="ew")

        self.next_button = ctk.CTkButton(
            top_controls,
            text="Next",
            command=self.next_frame,
            fg_color="gray"
        )
        self.next_button.grid(row=0, column=2, padx=8, pady=10, sticky="ew")

        content = ctk.CTkFrame(self.right_panel)
        content.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self.visualizer_container = ctk.CTkFrame(content)
        self.visualizer_container.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.visualizer_container.grid_columnconfigure(0, weight=1)
        self.visualizer_container.grid_rowconfigure(0, weight=1)

        self.visualizer_placeholder = ctk.CTkLabel(
            self.visualizer_container,
            text="Visualizer goes here",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.visualizer_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        bottom_panel = ctk.CTkFrame(content)
        bottom_panel.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        bottom_panel.grid_columnconfigure(0, weight=1)

        frame_label = ctk.CTkLabel(bottom_panel, text="Frame:")
        frame_label.grid(row=0, column=0, padx=15, pady=(12, 0), sticky="w")


        self.frame_slider = ctk.CTkSlider(bottom_panel, from_=0, to=100, command=self.on_frame_change)
        self.frame_slider.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="ew")

        speed_label = ctk.CTkLabel(bottom_panel, text="Playback speed (ms):")
        speed_label.grid(row=2, column=0, padx=15, pady=(5, 0), sticky="w")

        self.speed_entry = ctk.CTkEntry(bottom_panel)
        self.speed_entry.insert(0, "33")
        self.speed_entry.grid(row=3, column=0, padx=15, pady=(5, 15), sticky="ew")

        angles_label = ctk.CTkLabel(bottom_panel, text="Angles (deg):")
        angles_label.grid(row=4, column=0, padx=15, pady=(5, 0), sticky="w")

        self.angles_box = ctk.CTkTextbox(bottom_panel, height=150)
        self.angles_box.grid(row=5, column=0, padx=15, pady=(5, 15), sticky="nsew")
        self.angles_box.insert("1.0", "Angles will appear here.\n")

    def upload_video(self):
        path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv *.webm"),
            ],
        )
        if not path:
            return

        self.video_path = path
        self.file_label.configure(text=f"Selected:\n{path}")
        self.status_label.configure(text="Status: Video loaded, ready to analyze!")
        self.analyze_button.configure(state="normal")

    def analyze_video(self):
        if not self.video_path:
            messagebox.showwarning("Missing file", "Please upload a video first.")
            return

        self.status_label.configure(text=f"Status: analyzing {self.video_path}")
        self.angles_box.delete("1.0", "end")
        self.angles_box.insert("1.0", "Analysis output will be written here.\n")
        self.visualizer_placeholder.configure(text="Analysis running...")

        print(f"Analyzing: {self.video_path}")

    def toggle_play(self):
        print("Play / pause toggled")

    def prev_frame(self):
        print("Previous frame")

    def next_frame(self):
        print("Next frame")

    def on_frame_change(self, value):
        print(f"Frame changed to {int(float(value))}")

app = PoseAnalysisApp()
app.mainloop()
