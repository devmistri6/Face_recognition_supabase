import cv2
import numpy as np
import torch
import os
from io import BytesIO

import requests
from PIL import Image
from facenet_pytorch import MTCNN, InceptionResnetV1
from sklearn.preprocessing import LabelEncoder
from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name

from supabase import create_client, Client

class Recognizer:
    def __init__(self, details):
        self.details = details
        self.mtcnn = MTCNN(margin=20, keep_all=True)
        self.model = InceptionResnetV1(pretrained='vggface2').eval()

        # Anti-spoofing setup
        device_id = 0
        model_dir = "./resources/anti_spoof_models"
        self.spoof_model = AntiSpoofPredict(device_id)
        self.image_cropper = CropImage()
        self.models = [os.path.join(model_dir, model) for model in os.listdir(model_dir)]

        self.label_encoder = LabelEncoder()
        self.known_face_encodings = []
        self.known_face_labels = []

        # Supabase storage config
        url = "https://lcygbuvqtahekoghnpmx.supabase.co"
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxjeWdidXZxdGFoZWtvZ2hucG14Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDU0MDE0NiwiZXhwIjoyMDYwMTE2MTQ2fQ.S6DR83R-Uw4spJEXVpRnlG6dDGxeGF91PBha90S12Io"  # ⚠️ Store this securely (e.g., env var)
        supabase: Client = create_client(url, key)

        bucket = "userprofile"
        folder = f"students/{details['branch']}/{details['year']}/{details['section']}"

        # Fetch image filenames dynamically from Supabase
        try:
            files = supabase.storage.from_(bucket).list(path=folder)
            image_filenames = [file['name'] for file in files if file['name'].lower().endswith(('.jpg', '.jpeg', '.png'))]
        except Exception as e:
            print(f"❌ Failed to list files from Supabase: {e}")
            image_filenames = []

        base_url = f"{url}/storage/v1/object/public/{bucket}/{folder}"

        for filename in image_filenames:
            file_url = f"{base_url}/{filename}"
            try:
                response = requests.get(file_url)
                if response.status_code != 200:
                    print(f"❌ Could not load {file_url}")
                    continue

                img = Image.open(BytesIO(response.content)).convert("RGB")
                faces = self.mtcnn(img)

                if faces is None:
                    print(f"⚠️ No face detected in {filename}")
                    continue

                for face in faces:
                    embedding = self.model(face.unsqueeze(0)).detach().cpu().numpy()
                    embedding = embedding / np.linalg.norm(embedding)
                    self.known_face_encodings.append(embedding)
                    self.known_face_labels.append(filename.split('.')[0])
                    print(f"✅ Face from {filename} added.")

            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")

        self.label_encoder.fit(self.known_face_labels)
        self.recognition_threshold = 0.9
        self.recognized_students = set()


    def process_frame(self, frame, details=None):
        details = details or self.details
        boxes, probs = self.mtcnn.detect(frame)
        if boxes is not None:
            faces = self.mtcnn(frame)
            for i, face in enumerate(faces):
                x1, y1, x2, y2 = map(int, boxes[i])

                # Anti-spoof check
                prediction = np.zeros((1, 3))
                for model_path in self.models:
                    h_input, w_input, model_type, scale = parse_model_name(os.path.basename(model_path))
                    param = {"org_img": frame, "bbox": [x1, y1, x2 - x1, y2 - y1], "scale": scale, "out_w": w_input, "out_h": h_input}
                    img = self.image_cropper.crop(**param)
                    prediction += self.spoof_model.predict(img, model_path)

                label_spoof = np.argmax(prediction)
                if label_spoof == 1:  # Real face
                    embedding = self.model(face.unsqueeze(0)).detach().cpu().numpy()
                    embedding = embedding / np.linalg.norm(embedding)

                    distances = [np.linalg.norm(embedding - known) for known in self.known_face_encodings]
                    if distances:
                        min_index = np.argmin(distances)
                        min_dist = distances[min_index]
                        print(f"[INFO] Closest match: {self.known_face_labels[min_index]} | Distance: {min_dist}")

                        if min_dist < self.recognition_threshold:
                            label = self.known_face_labels[min_index]
                            self.recognized_students.add(label)
                        else:
                            label = "Unknown"

                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                else:
                    cv2.putText(frame, "Fake Face", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        return frame

    def get_recognized_students(self):
        return list(self.recognized_students)

    def get_details(self):
        return self.details
