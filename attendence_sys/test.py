from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
import numpy as np
import requests
from io import BytesIO
import torch

# Load image from Supabase
url = "https://lcygbuvqtahekoghnpmx.supabase.co/storage/v1/object/public/userprofile/students/CSE/1/A/2.jpg"
response = requests.get(url)
img = Image.open(BytesIO(response.content)).convert("RGB")

# Initialize models
mtcnn = MTCNN(keep_all=True)
resnet = InceptionResnetV1(pretrained="vggface2").eval()

# Detect face
faces = mtcnn(img)

if faces is None:
    print("❌ No face detected.")
else:
    print(f"✅ {len(faces)} face(s) detected.")
    for i, face in enumerate(faces):
        embedding = resnet(face.unsqueeze(0)).detach().numpy()
        print(f"Face {i+1} embedding (norm): {np.linalg.norm(embedding)}")
