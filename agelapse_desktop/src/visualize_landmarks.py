import os
import cv2
import numpy as np
from PIL import Image
import insightface
from insightface.app import FaceAnalysis
import matplotlib.pyplot as plt

# Initialize InsightFace model
face_app = FaceAnalysis(name='buffalo_l')
face_app.prepare(ctx_id=0, det_size=(640, 640))

def visualize_landmarks(image_path):
    # Read the image
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Detect faces
    faces = face_app.get(img)

    if not faces:
        print("No faces detected in the image.")
        return

    # Plot the image
    plt.figure(figsize=(12, 8))
    plt.imshow(img)

    # Plot landmarks for each detected face
    for face in faces:
        landmarks = face.landmark_2d_106
        for i, (x, y) in enumerate(landmarks):
            plt.plot(x, y, 'ro', markersize=2)
            plt.text(x, y, str(i), fontsize=6, color='white', 
                     bbox=dict(facecolor='red', alpha=0.5))

    plt.title("Face Landmarks")
    plt.axis('off')
    plt.show()

# Usage
image_path = "/Users/tomer.rosenfeld/Desktop/timelapse/images/yuval_non_cropped/cropped_2012-09-27 17.39.09.png"
visualize_landmarks(image_path)
