import os
import cv2
import tensorflow as tf
import numpy as np
import base64
from io import BytesIO
from flask import Flask, request, render_template

# Define the custom FixedDropout layer
class FixedDropout(tf.keras.layers.Dropout):
    def _get_noise_shape(self, inputs):
        if self.noise_shape is None:
            return self.noise_shape
        symbolic_shape = tf.keras.backend.shape(inputs)
        noise_shape = [symbolic_shape[axis] if shape is None else shape for axis, shape in enumerate(self.noise_shape)]
        return tuple(noise_shape)

# Register the custom FixedDropout layer with Keras
tf.keras.utils.get_custom_objects()['FixedDropout'] = FixedDropout

input_shape = (224, 224, 3)

def load_ben_color(path, sigmaX=10):
    image = cv2.imread(path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = crop_image_from_gray(image)
    image = cv2.resize(image, (input_shape[0], input_shape[1]))
    image = cv2.addWeighted(image, 4, cv2.GaussianBlur(image, (0, 0), sigmaX), -4, 128)
    return image

# Define the image cropping function (you can customize this based on your needs)
def crop_image_from_gray(img, tol=7):
    if img.ndim == 2:
        mask = img > tol
        return img[np.ix_(mask.any(1), mask.any(0))]
    elif img.ndim == 3:
        gray_img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        mask = gray_img > tol
        check_shape = img[:, :, 0][np.ix_(mask.any(1), mask.any(0))].shape[0]
        if check_shape == 0:
            return img
        else:
            img1 = img[:, :, 0][np.ix_(mask.any(1), mask.any(0))]
            img2 = img[:, :, 1][np.ix_(mask.any(1), mask.any(0))]
            img3 = img[:, :, 2][np.ix_(mask.any(1), mask.any(0))]
            img = np.stack([img1, img2, img3], axis=-1)
        return img

# Specify the path to download the model file
model_path = 'diabetic_retinopathy_detection_model.h5'

# Check if the model file already exists
if not os.path.isfile(model_path):
    # Download the model file from Google Cloud storage
    os.system('https://drive.google.com/file/d/1G9VGiSTi4XmnD9n-1G0wHjMCFdJqq9Zp/view?usp=drive_link' + model_path)

# Load the model
model = tf.keras.models.load_model(model_path)


# Initialize Flask app
app = Flask(__name__)

# Define the route for the home page
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Get the uploaded file
        file = request.files['file']
        # Save the uploaded file temporarily
        image_path = 'uploaded_image.jpg'
        file.save(image_path)

        # Load the original uploaded image
        original_image = cv2.imread(image_path)
        original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)

        # Preprocess the uploaded image
        preprocessed_image = load_ben_color(image_path)

        # Reshape the image for model input
        input_image = np.expand_dims(preprocessed_image, axis=0)

        # Make prediction
        prediction = predict_image(tf.convert_to_tensor(input_image))
        class_id = np.argmax(prediction)
        class_name = ['No DR', 'Mild', 'Moderate', 'Severe', 'Proliferative DR'][class_id]

        # Convert images to base64 encoding
        original_image_base64 = image_to_base64(original_image)
        preprocessed_image_base64 = image_to_base64(preprocessed_image)

        # Pass the necessary data to the HTML template
        return render_template('result.html', original_image=original_image_base64, preprocessed_image=preprocessed_image_base64, class_name=class_name)
    else:
        return render_template('index.html')

@tf.function
def predict_image(image):
    return model(image)

def image_to_base64(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode('.png', image_rgb)
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    return image_base64

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
