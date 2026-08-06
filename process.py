import json
from datetime import datetime
from pathlib import Path
import cv2
import mediapipe as mp


MODEL_PATH = Path(__file__).resolve().parent / "pose_landmarker_full.task"
RECORDINGS_DIR = Path(__file__).resolve().parent / "recordings"

def landmark_to_dict(landmark) -> dict[str, float]:
    return {
        "x": float(landmark.x),
        "y": float(landmark.y),
        "z": float(landmark.z),
        "visibility": float(getattr(landmark, "visibility", 0.0)),
    }


def process_video(video_filepath: Path | str, output_dir: Path | str = RECORDINGS_DIR) -> Path:
    video_filepath = Path(video_filepath)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_options = mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH))
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
    )

    frames: list[dict] = []

    with mp.tasks.vision.PoseLandmarker.create_from_options(options) as landmarker:
        cap = cv2.VideoCapture(str(video_filepath))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {video_filepath}")

        fps = cap.get(cv2.CAP_PROP_FPS)

        frame_index = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

            timestamp_ms = int(round((frame_index * 1000.0) / fps))
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            pose_landmarks = []
            if result.pose_landmarks:
                pose_landmarks = [landmark_to_dict(landmark) for landmark in result.pose_landmarks[0]]

            frames.append(
                {
                    "timestamp_ms": timestamp_ms,
                    "pose_landmarks": pose_landmarks,
                }
            )
            frame_index += 1

    output_path = output_dir / f"{video_filepath.stem}_{datetime.now().strftime('%m-%d-%H%M%S')}.json"
    with output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(frames, file_handle, indent=2)

    return output_path

        
