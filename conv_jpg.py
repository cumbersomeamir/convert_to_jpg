from flask import Flask, request, jsonify
import requests
from io import BytesIO
from PIL import Image
import base64
import boto3
import os
import time

app = Flask(__name__)

# Set up AWS S3 client using credentials from environment variables
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
    region_name=os.getenv('AWS_REGION')
)

@app.route('/convert_to_jpg', methods=['POST'])
def convert_to_jpg():
    try:
        # Get the image URL or base64 data from the request data
        data = request.json
        image_url = data.get('image_url')
        image_base64 = data.get('image_base64')

        if not image_url and not image_base64:
            return jsonify({'error': 'No image data provided'}), 400

        if image_url:
            # Fetch the image from the URL
            response = requests.get(image_url)
            
            if response.status_code != 200:
                return jsonify({'error': f'Failed to retrieve image, status code: {response.status_code}'}), 400
            
            image_data = BytesIO(response.content)

        elif image_base64:
            # Decode the base64 image data
            try:
                image_data = BytesIO(base64.b64decode(image_base64))
            except base64.binascii.Error as e:
                return jsonify({'error': f'Invalid base64 data: {str(e)}'}), 400

        # Open the image using PIL and convert to RGB
        image = Image.open(image_data)
        rgb_image = image.convert('RGB')
        
        # Save the converted image to a BytesIO object
        img_io = BytesIO()
        rgb_image.save(img_io, 'JPEG')
        img_io.seek(0)

        # Generate a unique file name for the image in S3
        s3_file_name = f"converted_image_{int(time.time())}.jpg"

        # Upload the image to S3
        s3_client.upload_fileobj(
            img_io,
            os.getenv('S3_BUCKET_NAME'),
            s3_file_name,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )

        # Generate the S3 URL for the uploaded image
        s3_url = f"https://{os.getenv('S3_BUCKET_NAME')}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_file_name}"

        # Return the S3 URL as the response
        return jsonify({'image_url': s3_url}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7010)
