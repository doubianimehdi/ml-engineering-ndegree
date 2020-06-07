import re
import os
import base64
from io import BytesIO

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dog_breed_classifier import DogBreedPrediction
from utility import download_blob

# keep model as global variable so we don't have to reload
# it in case of warm invocations
model = None

BUCKET_NAME = os.getenv('BUCKET_NAME', 'dog-breed-classifier')
SOURCE_BLOB_NAME = os.getenv('SOURCE_BLOB_NAME', 'model_transfer.pt')
DESTINATION_FILE_NAME = f'/tmp/{SOURCE_BLOB_NAME}'
BASE64_IMAGE_PATTERN = '^data:image/.+;base64,'

app = FastAPI()


class ImageData(BaseModel):
    base64: str


@app.get('/healthcheck')
def read_healthcheck():
    return 'healthy'


@app.post('/classify-dog-breeds')
def classify_dog_breeds(img_data: ImageData):
    global model

    if model is None:
        print(f'Initial startup, model content: {model}')
        download_blob(BUCKET_NAME, SOURCE_BLOB_NAME, DESTINATION_FILE_NAME)
        model = DogBreedPrediction(DESTINATION_FILE_NAME)

    # check input data is really an image
    if re.match(BASE64_IMAGE_PATTERN, img_data.base64):
        img_data = re.sub(BASE64_IMAGE_PATTERN, '', img_data.base64)
        try:
            img_path = BytesIO(base64.b64decode(img_data, validate=True))
            return model.predict(img_path)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail='There is a base64 decoding error.')
    else:
        raise HTTPException(
            status_code=400, detail='No image file found, please check again.')