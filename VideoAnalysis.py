import math
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox

from process import process_video


DATA_PATH = Path(__file__).resolve().parent / "recordings"

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32),
]

ANGLE_TRIPLETS = [
    (12, 24, 26),
    (11, 23, 25),
    (16, 14, 12),
    (11, 13, 15),
]

CANVAS_WIDTH = 800
CANVAS_HEIGHT = 800
POINT_RADIUS = 6
PAN_CURSOR = "fleur"
MIN_ZOOM = 0.25
MAX_ZOOM = 3.0
ZOOM_STEP = 1.1


def load_frames(path: Path) -> list[dict]:
    import json

    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def get_landmark_points(frame: dict) -> list[tuple[float, float]]:
    points = frame.get("pose_landmarks", [])
    return [(point.get("x", 0.0), point.get("y", 0.0)) for point in points]


def to_canvas_coords(x_norm: float, y_norm: float, width: int, height: int) -> tuple[int, int]:
    x = int(x_norm * width)
    y = int(y_norm * height)
    return x, y


def apply_view_transform(
    x: int,
    y: int,
    center_x: float,
    center_y: float,
    zoom: float,
    offset_x: float,
    offset_y: float,
) -> tuple[int, int]:
    transformed_x = center_x + ((x - center_x) * zoom) + offset_x
    transformed_y = center_y + ((y - center_y) * zoom) + offset_y
    return int(transformed_x), int(transformed_y)


def angle_between(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    v1 = (a[0] - b[0], a[1] - b[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = math.hypot(v1[0], v1[1])
    mag2 = math.hypot(v2[0], v2[1])
    cosang = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cosang))


class PoseAnalysisApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Pose Analysis")
        self.geometry("1500x800")
        self.minsize(1000, 800)

        self.video_path = None
        self.recording_path = None
        self.frames: list[dict] = []
        self.current_index = 0
        self.is_playing = False
        self._play_after_id = None
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self._pan_start_x = 0
        self._pan_start_y = 0
        self._pan_origin_x = 0.0
        self._pan_origin_y = 0.0
        self.zoom = 1.0

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.build_left_panel()
        self.build_right_panel()
        self.show_placeholder()
        self.set_controls_enabled(False)

    def build_left_panel(self):
        self.left_panel = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsw")
        self.left_panel.grid_propagate(False)
        self.left_panel.grid_rowconfigure(5, weight=1)

        title = ctk.CTkLabel(
            self.left_panel,
            text="Pose Analysis",
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

        self.play_button = ctk.CTkButton(
            top_controls,
            text="Play",
            command=self.toggle_play,
            fg_color="green",
        )
        self.play_button.grid(row=0, column=1, padx=8, pady=10, sticky="ew")

        content = ctk.CTkFrame(self.right_panel)
        content.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self.visualizer_container = ctk.CTkFrame(content)
        self.visualizer_container.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.visualizer_container.grid_columnconfigure(0, weight=1)
        self.visualizer_container.grid_rowconfigure(0, weight=1)

        self.canvas = ctk.CTkCanvas(
            self.visualizer_container,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.configure(cursor=PAN_CURSOR)
        self.canvas.bind("<ButtonPress-1>", self.on_pan_start)
        self.canvas.bind("<B1-Motion>", self.on_pan_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_pan_end)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        bottom_panel = ctk.CTkFrame(content)
        bottom_panel.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        bottom_panel.grid_columnconfigure(0, weight=1)

        frame_label = ctk.CTkLabel(bottom_panel, text="Frame:")
        frame_label.grid(row=0, column=0, padx=15, pady=(12, 0), sticky="w")

        self.frame_slider = ctk.CTkSlider(bottom_panel, from_=0, to=0, command=self.on_frame_change)
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
        self.angles_box.insert("1.0", "Angles\n")

    def set_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.play_button.configure(state=state)
        self.frame_slider.configure(state=state)

    def show_placeholder(self):
        self.canvas.delete("all")
        self.canvas.configure(bg="#E2E2E2")

    def upload_video(self):
        path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.webm")],
        )
        if not path:
            return

        self.video_path = path
        self.recording_path = None
        self.file_label.configure(text=f"Selected video:\n{path}")
        self.status_label.configure(text="Status: video loaded. Click Analyze to generate JSON and visualize.")

    def analyze_video(self):
        if not self.video_path:
            messagebox.showwarning("No video", "upload a video file before analyzing.")
            return
        try:
            self.status_label.configure(text="Status: processing video")
            self.update_idletasks()
            recording_path = process_video(Path(self.video_path), DATA_PATH)
            frames = load_frames(recording_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Unable to process video: {exc}")
            return

        self.recording_path = recording_path
        self.frames = frames
        self.current_index = 0
        self.is_playing = False
        self.zoom = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        if self._play_after_id:
            self.after_cancel(self._play_after_id)
            self._play_after_id = None

        self.frame_slider.configure(from_=0, to=len(self.frames) - 1 , number_of_steps=max(1, len(self.frames) - 1))
        self.frame_slider.set(0)
        self.set_controls_enabled(True)
        self.draw_frame(0)

        self.status_label.configure(text=f"Status: loaded {recording_path.name}")
        self.file_label.configure(text=f"Selected recording:\n{recording_path}")

    def on_frame_change(self, value):
        if not self.frames:
            return
        index = int(round(float(value)))
        self.current_index = index
        self.draw_frame(index)

    def prev_frame(self):
        if not self.frames:
            return
        index = max(0, self.current_index - 1)
        self.frame_slider.set(index)

    def next_frame(self):
        if not self.frames:
            return
        index = min(len(self.frames) - 1, self.current_index + 1)
        self.frame_slider.set(index)

    def toggle_play(self):
        if not self.frames:
            return

        self.is_playing = not self.is_playing
        self.play_button.configure(text="Pause" if self.is_playing else "Play")
        if self.is_playing:
            self._play_loop()
        elif self._play_after_id:
            self.after_cancel(self._play_after_id)
            self._play_after_id = None

    def _play_loop(self):
        if not self.is_playing or not self.frames:
            return

        next_index = (self.current_index + 1) % len(self.frames)
        self.current_index = next_index
        self.frame_slider.set(next_index)
        self.draw_frame(next_index)

        try:
            delay = int(self.speed_entry.get())
            if delay < 1:
                delay = 33
        except (ValueError, Exception):
            delay = 33

        self._play_after_id = self.after(delay, self._play_loop)

    def clear_canvas(self):
        self.canvas.delete("all")

    def on_pan_start(self, event):
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._pan_origin_x = self.pan_offset_x
        self._pan_origin_y = self.pan_offset_y

    def on_pan_drag(self, event):
        self.pan_offset_x = self._pan_origin_x + (event.x - self._pan_start_x)
        self.pan_offset_y = self._pan_origin_y + (event.y - self._pan_start_y)
        self.draw_frame(self.current_index)

    def on_pan_end(self, event):
        self.pan_offset_x = self._pan_origin_x + (event.x - self._pan_start_x)
        self.pan_offset_y = self._pan_origin_y + (event.y - self._pan_start_y)
        self.draw_frame(self.current_index)

    def on_mouse_wheel(self, event):
        if not self.frames:
            return

        scale_factor = ZOOM_STEP if event.delta > 0 else 1.0 / ZOOM_STEP
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * scale_factor))
        if new_zoom == self.zoom:
            return

        center_x = CANVAS_WIDTH / 2
        center_y = CANVAS_HEIGHT / 2
        cursor_x = event.x
        cursor_y = event.y
        self.pan_offset_x = cursor_x - center_x - ((cursor_x - center_x - self.pan_offset_x) * (new_zoom / self.zoom))
        self.pan_offset_y = cursor_y - center_y - ((cursor_y - center_y - self.pan_offset_y) * (new_zoom / self.zoom))
        self.zoom = new_zoom
        self.draw_frame(self.current_index)

    def _offset_point(self, x: int, y: int) -> tuple[int, int]:
        center_x = CANVAS_WIDTH / 2
        center_y = CANVAS_HEIGHT / 2
        return apply_view_transform(x, y, center_x, center_y, self.zoom, self.pan_offset_x, self.pan_offset_y)

    def draw_frame(self, index: int):
        if not (0 <= index < len(self.frames)):
            self.show_placeholder()
            return

        self.clear_canvas()
        frame = self.frames[index]
        points = get_landmark_points(frame)

        for start_index, end_index in POSE_CONNECTIONS:
            if start_index < len(points) and end_index < len(points):
                x1, y1 = to_canvas_coords(points[start_index][0], points[start_index][1], CANVAS_WIDTH, CANVAS_HEIGHT)
                x2, y2 = to_canvas_coords(points[end_index][0], points[end_index][1], CANVAS_WIDTH, CANVAS_HEIGHT)
                x1, y1 = self._offset_point(x1, y1)
                x2, y2 = self._offset_point(x2, y2)
                self.canvas.create_line(x1, y1, x2, y2, fill="#6aa3ff", width=2, smooth=True)

        for landmark_index, (nx, ny) in enumerate(points):
            x, y = to_canvas_coords(nx, ny, CANVAS_WIDTH, CANVAS_HEIGHT)
            x, y = self._offset_point(x, y)
            color = "#00533f" if landmark_index % 2 == 0 else "#ffb86b"
            self.canvas.create_oval(
                x - POINT_RADIUS,
                y - POINT_RADIUS,
                x + POINT_RADIUS,
                y + POINT_RADIUS,
                fill=color,
                outline="",
            )
            self.canvas.create_text(x + 10, y - 8, text=str(landmark_index), fill="#9e9e9e", font=("Helvetica", 9))

        angles_info = []
        for a_index, b_index, c_index in ANGLE_TRIPLETS:
            if a_index < len(points) and b_index < len(points) and c_index < len(points):
                a = to_canvas_coords(points[a_index][0], points[a_index][1], CANVAS_WIDTH, CANVAS_HEIGHT)
                b = to_canvas_coords(points[b_index][0], points[b_index][1], CANVAS_WIDTH, CANVAS_HEIGHT)
                c = to_canvas_coords(points[c_index][0], points[c_index][1], CANVAS_WIDTH, CANVAS_HEIGHT)
                a = self._offset_point(a[0], a[1])
                b = self._offset_point(b[0], b[1])
                c = self._offset_point(c[0], c[1])

                angle_value = angle_between(a, b, c)
                if not math.isnan(angle_value):
                    angles_info.append((a_index, b_index, c_index, angle_value))
                    self.canvas.create_line(a[0], a[1], b[0], b[1], fill="#ff7b7b", width=2)
                    self.canvas.create_line(b[0], b[1], c[0], c[1], fill="#ff7b7b", width=2)
                    self.canvas.create_line(c[0], c[1], a[0], a[1], fill="#ff7b7b", width=1, dash=(3, 5))
                    self.canvas.create_text(
                        b[0] + 12,
                        b[1] - 12,
                        text=f"{angle_value:.1f}°",
                        fill="#fff0f0",
                        font=("Helvetica", 12, "bold"),
                    )

        self.angles_box.configure(state="normal")
        self.angles_box.delete("1.0", "end")
        if angles_info:
            for a_index, b_index, c_index, angle_value in angles_info:
                self.angles_box.insert("end", f"{a_index} - {b_index} - {c_index}: {angle_value:.2f}°\n")
        else:
            self.angles_box.insert("end", "No angles available for this frame.\n")
        self.angles_box.configure(state="disabled")


if __name__ == "__main__":
    app = PoseAnalysisApp()
    app.mainloop()